"""
Export Module - Handles PDF generation and doctor sharing functionality
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
import secrets
import hashlib
from io import BytesIO
import logging
from pydantic import BaseModel
import json

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Cloud storage (using S3-compatible storage)
import boto3
from botocore.exceptions import ClientError

from supabase import create_client, Client

router = APIRouter(prefix="/api", tags=["export"])

# Initialize services
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# S3 configuration (can be Supabase Storage or AWS S3)
S3_BUCKET = os.getenv("S3_BUCKET", "proxima-health-exports")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

# Initialize S3 client if credentials are provided
s3_client = None
if S3_ACCESS_KEY and S3_SECRET_KEY:
    s3_client = boto3.client(
        's3',
        region_name=S3_REGION,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY
    )

# Request models
class ExportPDFRequest(BaseModel):
    user_id: str
    story_ids: List[str]
    include_analysis: bool = True
    include_notes: bool = True
    date_range: Optional[Dict[str, str]] = None  # {"start": "2024-01-01", "end": "2024-01-31"}

class ShareWithDoctorRequest(BaseModel):
    user_id: str
    story_ids: List[str]
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    expires_in_days: int = 30
    include_analysis: bool = True

class EmailShareRequest(BaseModel):
    share_link: str
    recipient_email: str

def generate_secure_token(user_id: str, story_ids: List[str]) -> str:
    """Generate a secure, unguessable share token"""
    # Create unique data
    data = f"{user_id}:{':'.join(sorted(story_ids))}:{datetime.utcnow().isoformat()}"
    
    # Generate random component
    random_component = secrets.token_urlsafe(32)
    
    # Create hash for verification
    hash_component = hashlib.sha256(data.encode()).hexdigest()[:16]
    
    # Combine for final token
    return f"{random_component}-{hash_component}"

async def get_user_info(user_id: str) -> Dict:
    """Get user information for the report"""
    try:
        # Get user profile
        profile = supabase.table('profiles').select('*').eq('user_id', user_id).single().execute()
        return profile.data if profile.data else {'name': 'User', 'email': 'Not provided'}
    except:
        return {'name': 'User', 'email': 'Not provided'}

async def get_stories_with_analysis(story_ids: List[str]) -> Dict:
    """Get stories with their associated analysis"""
    stories_data = []
    
    for story_id in story_ids:
        # Get story
        story_result = supabase.table('health_stories').select('*').eq('id', story_id).single().execute()
        if not story_result.data:
            continue
        
        story = story_result.data
        
        # Get associated analysis
        insights = supabase.table('health_insights').select('*').eq(
            'story_id', story_id
        ).order('confidence.desc').execute()
        
        predictions = supabase.table('health_predictions').select('*').eq(
            'story_id', story_id
        ).order('probability.desc').execute()
        
        # Get any notes
        notes = supabase.table('story_notes').select('*').eq(
            'story_id', story_id
        ).execute()
        
        stories_data.append({
            'story': story,
            'insights': insights.data if insights.data else [],
            'predictions': predictions.data if predictions.data else [],
            'notes': {'content': notes.data[0]['note_text']} if notes.data else None
        })
    
    return stories_data

def create_pdf_styles():
    """Create custom styles for the PDF"""
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#6B46C1'),
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#6B46C1'),
        spaceAfter=20,
        spaceBefore=30
    ))
    
    styles.add(ParagraphStyle(
        name='InsightPositive',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        textColor=colors.HexColor('#10b981')
    ))
    
    styles.add(ParagraphStyle(
        name='InsightWarning',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        textColor=colors.HexColor('#f59e0b')
    ))
    
    styles.add(ParagraphStyle(
        name='InsightNeutral',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        textColor=colors.HexColor('#6b7280')
    ))
    
    return styles

async def generate_health_report_pdf(user_id: str, stories_data: List[Dict], 
                                   include_analysis: bool, include_notes: bool) -> BytesIO:
    """Generate a professional health report PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    elements = []
    styles = create_pdf_styles()
    
    # Get user info
    user_info = await get_user_info(user_id)
    
    # Title page
    elements.append(Paragraph("Health Intelligence Report", styles['CustomTitle']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Report metadata
    elements.append(Paragraph(f"<b>Prepared for:</b> {user_info.get('name', 'User')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Report Period:</b> {len(stories_data)} health stories included", styles['Normal']))
    elements.append(Spacer(1, 0.5*inch))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        borderColor=colors.HexColor('#e5e7eb'),
        borderWidth=1,
        borderPadding=10,
        backColor=colors.HexColor('#f9fafb')
    )
    
    elements.append(Paragraph(
        "<b>Important:</b> This report is for informational purposes only and does not constitute medical advice. "
        "Always consult with qualified healthcare professionals for medical decisions.",
        disclaimer_style
    ))
    
    elements.append(PageBreak())
    
    # Process each story
    for idx, data in enumerate(stories_data):
        story = data['story']
        
        # Story header
        elements.append(Paragraph(f"Health Story #{idx + 1}", styles['SectionTitle']))
        elements.append(Paragraph(f"Week of {story['created_at'][:10]}", styles['Italic']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Story content
        elements.append(Paragraph(story['story_text'], styles['Normal']))
        
        # Personal note if included
        if include_notes and data.get('notes'):
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("<b>Personal Note:</b>", styles['Heading3']))
            elements.append(Paragraph(data['notes']['content'], styles['Italic']))
        
        # Analysis section
        if include_analysis:
            elements.append(Spacer(1, 0.3*inch))
            
            # Insights
            if data['insights']:
                elements.append(Paragraph("Key Insights", styles['Heading3']))
                for insight in data['insights']:
                    style_name = f"Insight{insight['insight_type'].capitalize()}"
                    if style_name not in styles:
                        style_name = 'Normal'
                    
                    elements.append(Paragraph(
                        f"• <b>{insight['title']}</b> - {insight['description']} "
                        f"<i>(Confidence: {insight['confidence']}%)</i>",
                        styles[style_name]
                    ))
                elements.append(Spacer(1, 0.2*inch))
            
            # Predictions
            if data['predictions']:
                elements.append(Paragraph("Health Outlook", styles['Heading3']))
                for pred in data['predictions']:
                    preventable_text = " (Preventable)" if pred.get('preventable') else ""
                    elements.append(Paragraph(
                        f"• {pred['event_description']} - {pred['probability']}% likelihood "
                        f"{pred['timeframe'].lower()}{preventable_text}",
                        styles['Normal']
                    ))
                    if pred.get('reasoning'):
                        elements.append(Paragraph(
                            f"  <i>Reasoning: {pred['reasoning']}</i>",
                            styles['Italic']
                        ))
                elements.append(Spacer(1, 0.2*inch))
        
        # Add page break between stories (except for last one)
        if idx < len(stories_data) - 1:
            elements.append(PageBreak())
    
    # Summary page
    if include_analysis and len(stories_data) > 1:
        elements.append(PageBreak())
        elements.append(Paragraph("Summary Analysis", styles['SectionTitle']))
        
        # Aggregate insights
        total_insights = sum(len(d['insights']) for d in stories_data)
        total_predictions = sum(len(d['predictions']) for d in stories_data)
        
        elements.append(Paragraph(
            f"Across {len(stories_data)} health stories, we identified {total_insights} key insights "
            f"and {total_predictions} health predictions.",
            styles['Normal']
        ))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(
        "Generated by Proxima-1 Health Intelligence • proxima-1.health",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#9ca3af')
        )
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

async def upload_to_storage(file_buffer: BytesIO, user_id: str, filename: str) -> str:
    """Upload file to cloud storage and return URL"""
    if s3_client:
        # Use S3
        try:
            key = f"exports/{user_id}/{filename}"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=file_buffer.getvalue(),
                ContentType='application/pdf',
                Metadata={
                    'user_id': user_id,
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
            
            # Generate presigned URL (valid for 1 hour)
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': key},
                ExpiresIn=3600
            )
            return url
            
        except ClientError as e:
            logging.error(f"S3 upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload PDF")
    else:
        # Fallback: Use Supabase Storage
        try:
            file_buffer.seek(0)
            filename = f"{user_id}/{filename}"
            
            response = supabase.storage.from_('exports').upload(
                file=file_buffer.read(),
                path=filename,
                file_options={"content-type": "application/pdf"}
            )
            
            # Get public URL
            url = supabase.storage.from_('exports').get_public_url(filename)
            return url
            
        except Exception as e:
            logging.error(f"Supabase storage upload failed: {str(e)}")
            # Return a data URL as last resort
            file_buffer.seek(0)
            import base64
            data = base64.b64encode(file_buffer.read()).decode()
            return f"data:application/pdf;base64,{data}"

@router.post("/export-pdf")
async def export_pdf(request: ExportPDFRequest):
    """Generate and export a PDF health report"""
    try:
        # Get stories with analysis
        stories_data = await get_stories_with_analysis(request.story_ids)
        
        if not stories_data:
            raise HTTPException(status_code=404, detail="No stories found")
        
        # Generate PDF
        pdf_buffer = await generate_health_report_pdf(
            user_id=request.user_id,
            stories_data=stories_data,
            include_analysis=request.include_analysis,
            include_notes=request.include_notes
        )
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"health_report_{timestamp}.pdf"
        
        # Upload to storage
        pdf_url = await upload_to_storage(pdf_buffer, request.user_id, filename)
        
        # Record export in database
        export_record = supabase.table('export_history').insert({
            'user_id': request.user_id,
            'export_type': 'pdf',
            'story_ids': request.story_ids,
            'file_url': pdf_url,
            'file_size_bytes': len(pdf_buffer.getvalue()),
            'metadata': {
                'include_analysis': request.include_analysis,
                'include_notes': request.include_notes,
                'stories_count': len(stories_data)
            }
        }).execute()
        
        return {
            'status': 'success',
            'pdf_url': pdf_url,
            'expires_in': 3600,  # 1 hour
            'export_id': export_record.data[0]['id'],
            'file_size': len(pdf_buffer.getvalue())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"PDF export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.post("/share-with-doctor")
async def share_with_doctor(request: ShareWithDoctorRequest):
    """Create a secure share link for healthcare providers"""
    try:
        # Generate unique share token
        share_token = generate_secure_token(request.user_id, request.story_ids)
        share_link = f"https://proxima-1.health/shared/{share_token}"
        
        # Calculate expiration
        expires_at = None
        if request.expires_in_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Create share record
        share_record = supabase.table('export_history').insert({
            'user_id': request.user_id,
            'export_type': 'doctor_share',
            'story_ids': request.story_ids,
            'share_token': share_token,
            'share_link': share_link,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'recipient_email': request.recipient_email,
            'recipient_name': request.recipient_name,
            'metadata': {
                'include_analysis': request.include_analysis
            }
        }).execute()
        
        # Send email notification if requested
        if request.recipient_email:
            # TODO: Implement email sending
            pass
        
        return {
            'status': 'success',
            'share_link': share_link,
            'share_token': share_token,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'export_id': share_record.data[0]['id']
        }
        
    except Exception as e:
        logging.error(f"Share creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Share creation failed: {str(e)}")

@router.get("/shared/{share_token}")
async def view_shared_report(share_token: str):
    """View a shared health report (for doctors)"""
    try:
        # Validate share token
        share_record = supabase.table('export_history').select('*').eq(
            'share_token', share_token
        ).single().execute()
        
        if not share_record.data:
            raise HTTPException(status_code=404, detail="Share link not found")
        
        record = share_record.data
        
        # Check expiration
        if record.get('expires_at'):
            expires = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
            if expires < datetime.utcnow():
                raise HTTPException(status_code=410, detail="Share link has expired")
        
        # Increment access count
        supabase.table('export_history').update({
            'access_count': record.get('access_count', 0) + 1,
            'last_accessed_at': datetime.utcnow().isoformat()
        }).eq('id', record['id']).execute()
        
        # Get stories and analysis
        stories_data = await get_stories_with_analysis(record['story_ids'])
        
        # Get user info (limited for privacy)
        user_info = await get_user_info(record['user_id'])
        
        # Create HTML response
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Health Report - Proxima-1</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #6B46C1;
                    border-bottom: 3px solid #6B46C1;
                    padding-bottom: 10px;
                }}
                .metadata {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 30px;
                }}
                .story {{
                    margin-bottom: 40px;
                    padding-bottom: 40px;
                    border-bottom: 1px solid #e0e0e0;
                }}
                .insight {{
                    margin: 10px 0;
                    padding: 10px;
                    border-left: 4px solid;
                    background: #f8f9fa;
                }}
                .insight.positive {{ border-color: #10b981; }}
                .insight.warning {{ border-color: #f59e0b; }}
                .insight.neutral {{ border-color: #6b7280; }}
                .prediction {{
                    margin: 10px 0;
                    padding: 10px;
                    background: #e8f4fd;
                    border-radius: 5px;
                }}
                .disclaimer {{
                    margin-top: 40px;
                    padding: 20px;
                    background: #fef3c7;
                    border: 1px solid #fbbf24;
                    border-radius: 5px;
                    font-size: 14px;
                }}
                @media print {{
                    body {{ background: white; }}
                    .container {{ box-shadow: none; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Health Intelligence Report</h1>
                
                <div class="metadata">
                    <p><strong>Patient ID:</strong> {record['user_id'][:8]}...</p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                    <p><strong>Stories Included:</strong> {len(stories_data)}</p>
                    <p><strong>Access Count:</strong> {record.get('access_count', 0) + 1}</p>
                </div>
                
                {"".join(generate_story_html(data) for data in stories_data)}
                
                <div class="disclaimer">
                    <strong>Medical Disclaimer:</strong> This report is generated from patient-reported data 
                    and AI analysis. It is for informational purposes only and should not replace 
                    professional medical judgment. Please correlate with clinical findings and patient history.
                </div>
                
                <p style="text-align: center; color: #999; margin-top: 40px;">
                    Generated by Proxima-1 Health Intelligence • 
                    <a href="https://proxima-1.health" style="color: #6B46C1;">proxima-1.health</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to view shared report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load report")

def generate_story_html(data: Dict) -> str:
    """Generate HTML for a single story"""
    story = data['story']
    html = f"""
    <div class="story">
        <h2>Health Story - {story['created_at'][:10]}</h2>
        <p>{story['content']}</p>
    """
    
    if data['insights']:
        html += "<h3>Key Insights</h3>"
        for insight in data['insights']:
            html += f"""
            <div class="insight {insight['insight_type']}">
                <strong>{insight['title']}</strong><br>
                {insight['description']}<br>
                <small>Confidence: {insight['confidence']}%</small>
            </div>
            """
    
    if data['predictions']:
        html += "<h3>Health Predictions</h3>"
        for pred in data['predictions']:
            html += f"""
            <div class="prediction">
                <strong>{pred['event_description']}</strong><br>
                Probability: {pred['probability']}% • Timeframe: {pred['timeframe']}<br>
                {f"<small>{pred.get('reasoning', '')}</small>" if pred.get('reasoning') else ""}
            </div>
            """
    
    html += "</div>"
    return html

@router.post("/share/send-email")
async def send_share_email(request: EmailShareRequest):
    """Send share link via email"""
    # TODO: Implement email sending via SendGrid, AWS SES, or similar
    return {
        'status': 'success',
        'message': 'Email functionality not yet implemented'
    }