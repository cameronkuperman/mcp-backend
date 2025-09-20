"""
Email Service Module - SendGrid Integration with Production Features
Handles email delivery for medical reports, quick scans, and notifications
"""

import os
import json
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from functools import wraps
import asyncio

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator
import sendgrid
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Attachment, 
    FileContent, FileName, FileType, Disposition
)
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import httpx
from supabase import create_client, Client
import logging

# Models
from models.requests import EmailReportRequest, EmailScanRequest, EmailResponse

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/email", tags=["email"])

# Initialize SendGrid client
sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend
supabase: Client = create_client(supabase_url, supabase_key)

# Constants
MAX_ATTACHMENT_SIZE_MB = 10
MAX_EMAILS_PER_HOUR = 5
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "reports@seimeo.health")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Seimeo Health Platform")

# Email Request Models
class EmailReportRequest(BaseModel):
    to: EmailStr
    cc: Optional[List[EmailStr]] = []
    subject: Optional[str] = "Your Seimeo Health Assessment"
    template: str = "patient"  # patient, doctor, employer
    attachment: Dict[str, Any]  # filename, content (base64), type
    custom_message: Optional[str] = None
    scan_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    
    @validator('attachment')
    def validate_attachment(cls, v):
        if 'content' not in v or 'filename' not in v:
            raise ValueError("Attachment must have 'content' and 'filename'")
        
        # Check size (base64 is ~1.33x larger than binary)
        content_size_mb = len(v['content']) / (1024 * 1024 * 1.33)
        if content_size_mb > MAX_ATTACHMENT_SIZE_MB:
            raise ValueError(f"Attachment exceeds {MAX_ATTACHMENT_SIZE_MB}MB limit")
        
        return v

class EmailScanRequest(BaseModel):
    to: EmailStr
    subject: Optional[str] = "Your Quick Scan Results"
    template: str = "quick_scan"
    data: Dict[str, Any]  # Quick scan data
    scan_id: str

# Retry decorator with exponential backoff
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def send_with_retry(mail: Mail) -> str:
    """Send email with automatic retry on failure"""
    try:
        response = sg.send(mail)
        # SendGrid returns message ID in headers
        return response.headers.get('X-Message-Id', str(uuid.uuid4()))
    except Exception as e:
        logger.error(f"SendGrid send failed: {str(e)}")
        raise

async def verify_scan_ownership(scan_id: str, user_id: str, scan_type: str = "quick_scans") -> bool:
    """Verify that the user owns the scan"""
    try:
        result = supabase.table(scan_type).select("id").eq("id", scan_id).eq("user_id", user_id).single().execute()
        return result.data is not None
    except:
        return False

def generate_idempotency_key(user_id: str, email_type: str, recipient: str, source_id: Optional[str] = None) -> str:
    """Generate idempotency key to prevent duplicate sends"""
    hour_bucket = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()
    key_parts = [user_id or "anon", email_type, recipient, source_id or "", hour_bucket]
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()

async def log_email_event(aggregate_id: str, user_id: str, event_type: str, event_data: Dict) -> None:
    """Log email event for audit trail"""
    try:
        supabase.table("email_events").insert({
            "aggregate_id": aggregate_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log email event: {str(e)}")

async def queue_email(email_data: Dict) -> str:
    """Add email to send queue"""
    try:
        result = supabase.table("email_send_queue").insert(email_data).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        # Check if it's a duplicate (idempotency key violation)
        if "duplicate key" in str(e).lower():
            # Return existing queue item
            existing = supabase.table("email_send_queue").select("id").eq(
                "idempotency_key", email_data["idempotency_key"]
            ).single().execute()
            return existing.data["id"] if existing.data else None
        raise

def build_email_html(template: str, data: Dict) -> str:
    """Build email HTML from template and data"""
    # TODO: Use proper templating engine like Jinja2
    # For now, basic template
    if template == "patient":
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Your Medical Report</h2>
            <p>Dear Patient,</p>
            <p>Your medical assessment report is attached to this email.</p>
            {f'<p>{data.get("custom_message", "")}</p>' if data.get("custom_message") else ''}
            <p>Please review the attached PDF for detailed information about your health assessment.</p>
            <hr style="border: 1px solid #ecf0f1;">
            <p style="font-size: 12px; color: #7f8c8d;">
                This email contains confidential medical information. 
                Please do not forward without authorization.
            </p>
        </body>
        </html>
        """
    elif template == "quick_scan":
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Quick Scan Results</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>Body Part:</strong> {data.get('bodyPart', 'N/A')}</p>
                <p><strong>Primary Condition:</strong> {data.get('primaryCondition', 'N/A')}</p>
                <p><strong>Confidence:</strong> {data.get('confidence', 0)}%</p>
            </div>
            <h3>Recommendations:</h3>
            <ul>
                {''.join([f'<li>{r}</li>' for r in data.get('recommendations', [])])}
            </ul>
            <p style="margin-top: 20px;">
                <a href="https://healthoracle.ai/scan/{data.get('scanId', '')}" 
                   style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   View Full Report
                </a>
            </p>
        </body>
        </html>
        """
    else:
        return f"<html><body><p>Medical report attached.</p></body></html>"

# Endpoints

@router.post("/send-report", response_model=EmailResponse)
async def send_medical_report(
    request: EmailReportRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None  # Get from auth in production
):
    """Send medical report PDF via email"""
    try:
        # Generate aggregate ID for event tracking
        aggregate_id = str(uuid.uuid4())
        
        # Verify scan ownership if scan_id provided
        if request.scan_id and user_id:
            if not await verify_scan_ownership(request.scan_id, user_id):
                raise HTTPException(403, "Unauthorized: You don't own this scan")
        
        # Generate idempotency key
        idempotency_key = generate_idempotency_key(
            user_id or "anon",
            "medical_report",
            request.to,
            request.scan_id
        )
        
        # Check if already sent (within same hour)
        existing = supabase.table("email_send_queue").select("id", "status", "sent_at").eq(
            "idempotency_key", idempotency_key
        ).execute()
        
        if existing.data and existing.data[0]["status"] in ["sent", "delivered"]:
            return EmailResponse(
                success=True,
                message_id=existing.data[0]["id"],
                sent_at=existing.data[0]["sent_at"],
                message="Email already sent within this hour"
            )
        
        # Log email requested event
        await log_email_event(
            aggregate_id, 
            user_id or "anon",
            "email_requested",
            {"to": request.to, "template": request.template}
        )
        
        # Queue email for sending
        queue_data = {
            "user_id": user_id or "anon",
            "recipient_email": request.to,
            "cc_emails": request.cc or [],
            "email_type": "medical_report",
            "subject": request.subject,
            "template": request.template,
            "template_data": {
                "custom_message": request.custom_message,
                "scan_date": datetime.now().strftime("%B %d, %Y")
            },
            "attachment_metadata": {
                "filename": request.attachment["filename"],
                "size_kb": len(request.attachment["content"]) // 1024,
                "content_type": request.attachment.get("type", "application/pdf"),
                "has_phi": True
            },
            "attachment_content": request.attachment["content"],
            "idempotency_key": idempotency_key,
            "metadata": request.metadata,
            "priority": 5
        }
        
        queue_id = await queue_email(queue_data)
        
        # Send email in background
        background_tasks.add_task(process_email_queue_item, queue_id, aggregate_id)
        
        return EmailResponse(
            success=True,
            message_id=queue_id,
            sent_at=datetime.now().isoformat(),
            message="Email queued for delivery"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email send failed: {str(e)}")
        raise HTTPException(500, f"Failed to send email: {str(e)}")

@router.post("/send-scan", response_model=EmailResponse)
async def send_quick_scan(
    request: EmailScanRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None
):
    """Send quick scan results without PDF attachment"""
    try:
        aggregate_id = str(uuid.uuid4())
        
        # Verify scan ownership
        if user_id and not await verify_scan_ownership(request.scan_id, user_id):
            raise HTTPException(403, "Unauthorized: You don't own this scan")
        
        # Build email
        mail = Mail(
            from_email=Email(EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME),
            to_emails=To(request.to),
            subject=request.subject,
            html_content=Content("text/html", build_email_html("quick_scan", request.data))
        )
        
        # Send with retry
        message_id = await send_with_retry(mail)
        
        # Log success
        await log_email_event(
            aggregate_id,
            user_id or "anon",
            "email_sent",
            {"to": request.to, "message_id": message_id}
        )
        
        return EmailResponse(
            success=True,
            message_id=message_id,
            sent_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Quick scan email failed: {str(e)}")
        raise HTTPException(500, f"Failed to send email: {str(e)}")

@router.post("/webhooks/sendgrid")
async def handle_sendgrid_webhook(
    events: List[Dict],
    authorization: Optional[str] = Header(None)
):
    """Handle SendGrid webhook events"""
    try:
        # TODO: Verify webhook signature
        # if not verify_sendgrid_signature(authorization, events):
        #     raise HTTPException(401, "Invalid webhook signature")
        
        for event in events:
            # Log raw webhook
            supabase.table("sendgrid_webhooks").insert({
                "message_id": event.get("sg_message_id", "").split(".")[0],
                "event_type": event.get("event"),
                "email": event.get("email"),
                "timestamp": datetime.fromtimestamp(event.get("timestamp", 0)).isoformat(),
                "raw_event": event
            }).execute()
            
            # Update email queue status based on event
            message_id = event.get("sg_message_id", "").split(".")[0]
            event_type = event.get("event")
            
            if message_id and event_type:
                status_map = {
                    "delivered": "delivered",
                    "bounce": "bounced",
                    "dropped": "failed",
                    "deferred": "failed"
                }
                
                if event_type in status_map:
                    supabase.table("email_send_queue").update({
                        "status": status_map[event_type],
                        "metadata": {"sendgrid_event": event}
                    }).eq("sendgrid_message_id", message_id).execute()
        
        return {"success": True, "processed": len(events)}
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        return {"success": False, "error": str(e)}

# Background task processor
async def process_email_queue_item(queue_id: str, aggregate_id: str):
    """Process queued email asynchronously"""
    try:
        # Get queue item
        result = supabase.table("email_send_queue").select("*").eq("id", queue_id).single().execute()
        if not result.data:
            return
        
        item = result.data
        
        # Update status to sending
        supabase.table("email_send_queue").update({"status": "sending"}).eq("id", queue_id).execute()
        
        # Build email
        mail = Mail(
            from_email=Email(EMAIL_FROM_ADDRESS, EMAIL_FROM_NAME),
            to_emails=To(item["recipient_email"]),
            subject=item["subject"],
            html_content=Content("text/html", build_email_html(item["template"], item["template_data"]))
        )
        
        # Add CC if present
        if item.get("cc_emails"):
            for cc in item["cc_emails"]:
                mail.add_cc(cc)
        
        # Add attachment if present
        if item.get("attachment_content"):
            attachment = Attachment()
            attachment.file_content = FileContent(item["attachment_content"])
            attachment.file_name = FileName(item["attachment_metadata"]["filename"])
            attachment.file_type = FileType(item["attachment_metadata"].get("content_type", "application/pdf"))
            attachment.disposition = Disposition("attachment")
            mail.attachment = attachment
        
        # Send with retry
        message_id = await send_with_retry(mail)
        
        # Update queue item
        supabase.table("email_send_queue").update({
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "sendgrid_message_id": message_id
        }).eq("id", queue_id).execute()
        
        # Log success event
        await log_email_event(
            aggregate_id,
            item["user_id"],
            "email_sent",
            {"message_id": message_id}
        )
        
    except Exception as e:
        logger.error(f"Queue processing failed for {queue_id}: {str(e)}")
        
        # Update queue item with failure
        supabase.table("email_send_queue").update({
            "status": "failed",
            "retry_count": item.get("retry_count", 0) + 1,
            "error_message": str(e),
            "next_retry_at": (datetime.now() + timedelta(minutes=5 * (item.get("retry_count", 0) + 1))).isoformat()
        }).eq("id", queue_id).execute()
        
        # Log failure event
        await log_email_event(
            aggregate_id,
            item["user_id"],
            "email_failed",
            {"error": str(e)}
        )

# Health check endpoint
@router.get("/health")
async def email_health_check():
    """Check email service health"""
    try:
        # Check SendGrid API key
        if not os.getenv('SENDGRID_API_KEY'):
            return {"status": "unhealthy", "error": "SendGrid API key not configured"}
        
        # Check Supabase connection
        result = supabase.table("email_send_queue").select("count").execute()
        
        return {
            "status": "healthy",
            "sendgrid": "configured",
            "database": "connected"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}