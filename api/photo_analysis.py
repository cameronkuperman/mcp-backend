"""Photo Analysis API endpoints"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import base64
import io
import os
import json
from datetime import datetime, timedelta
import httpx
from supabase import create_client
import uuid

from models.requests import (
    PhotoCategorizeResponse,
    PhotoUploadResponse, 
    PhotoAnalysisRequest,
    PhotoAnalysisResponse,
    PhotoSessionResponse
)
from utils.json_parser import extract_json_from_text

router = APIRouter(prefix="/api/photo-analysis", tags=["photo-analysis"])

import re

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing special characters and unicode spaces"""
    # Replace unicode spaces with regular spaces
    filename = re.sub(r'[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000\uFEFF]', ' ', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Remove or replace other special characters (keep only alphanumeric, spaces, dots, dashes, underscores)
    filename = re.sub(r'[^a-zA-Z0-9\s._-]', '', filename)
    # Trim spaces
    filename = filename.strip()
    # If filename is empty after sanitization, use a default
    if not filename:
        filename = "photo.jpg"
    return filename

@router.get("/health")
async def health_check():
    """Health check endpoint for photo analysis"""
    return {
        "status": "ok",
        "service": "photo-analysis",
        "database_connected": supabase is not None,
        "openrouter_configured": OPENROUTER_API_KEY is not None,
        "storage_configured": SUPABASE_URL is not None,
        "storage_bucket": STORAGE_BUCKET
    }

@router.get("/debug/storage")
async def debug_storage():
    """Debug endpoint to test storage configuration"""
    if not supabase:
        return {"error": "Supabase not configured"}
    
    try:
        # List buckets
        buckets = supabase.storage.list_buckets()
        
        # Check if our bucket exists
        bucket_exists = any(b['name'] == STORAGE_BUCKET for b in buckets)
        
        return {
            "storage_bucket": STORAGE_BUCKET,
            "bucket_exists": bucket_exists,
            "available_buckets": [b['name'] for b in buckets],
            "supabase_url": SUPABASE_URL is not None,
            "using_service_key": SUPABASE_SERVICE_KEY is not None
        }
    except Exception as e:
        return {
            "error": str(e),
            "storage_bucket": STORAGE_BUCKET
        }

# OPTIONS handling is done by CORS middleware, no need for manual handler

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize Supabase client only if credentials are available
supabase = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
elif SUPABASE_URL and SUPABASE_ANON_KEY:
    # Fallback to anon key if service key not available
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("Warning: Using ANON key for photo analysis. Some operations may be limited.")

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp']
STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'medical-photos')

# AI Prompts
PHOTO_CATEGORIZATION_PROMPT = """You are a medical photo categorization system. Analyze the image and categorize it into EXACTLY ONE of these categories:

CATEGORIES:
- medical_normal: ANY legitimate medical condition that is NOT in intimate/private areas, including:
  * Dermatological: rashes, acne, eczema, psoriasis, moles, skin cancer, hives, burns
  * Orthopedic: visible fractures, joint deformities, swelling, sprains, dislocations
  * Soft tissue: muscle tears, bruising, hematomas, cellulitis, abscesses
  * Vascular: varicose veins, spider veins, venous insufficiency signs
  * Wounds: cuts, lacerations, abrasions, ulcers, surgical incisions (healed)
  * Inflammatory: arthritis, bursitis, tendinitis visible signs
  * Infectious: visible infections, fungal conditions, bacterial skin infections
  * Allergic: reactions, contact dermatitis, urticaria
  * Systemic disease signs: jaundice, cyanosis, edema, lymphadenopathy
  * Eye conditions: conjunctivitis, styes, periorbital issues
  * Nail conditions: fungal infections, ingrown nails, nail trauma
  * Hair/scalp: alopecia, scalp conditions, folliculitis
  * ANY other visible medical condition NOT in private areas

- medical_sensitive: Medical conditions involving intimate areas (even if legitimate):
  * Penis, vulva, vagina, or genital conditions
  * Anus or anal conditions
  * Perineal area conditions
  * NOTE: Regular buttocks/gluteal area WITHOUT anus visible = medical_normal
  * NOTE: Breast conditions = medical_normal (unless nipple area)

- medical_gore: Severe/graphic medical content (still medical and legal):
  * Active surgical procedures
  * Deep wounds with exposed tissue/bone/tendons
  * Severe trauma or accidents
  * Major burns (3rd/4th degree)
  * Amputations or severe deformities
  * Compound fractures with bone exposure

- unclear: Photo quality prevents medical assessment:
  * Too blurry to identify condition
  * Too dark or overexposed
  * Too far away to see medical detail
  * Obscured by clothing/objects

- non_medical: Clearly not medical:
  * Objects, food, pets, landscapes
  * Normal body parts without any condition
  * Non-medical selfies or photos

- inappropriate: ONLY illegal content (extremely rare)

IMPORTANT: Be inclusive - almost any human body photo showing a potential medical issue should be categorized as medical_normal unless it meets specific criteria for other categories.

CRITICAL CLARIFICATIONS:
- Buttocks/glutes WITHOUT anus visible = medical_normal
- Chest/breast area WITHOUT nipple = medical_normal  
- Only categorize as medical_sensitive if genitals (penis/vulva/vagina) or anus are ACTUALLY VISIBLE
- Err on the side of medical_normal when uncertain

Respond with ONLY this JSON format:
{
  "category": "category_name",
  "confidence": 0.95,
  "subcategory": "specific_condition_type (e.g., 'dermatological_rash', 'orthopedic_fracture', 'vascular_varicose')"
}"""

PHOTO_ANALYSIS_PROMPT = """You are an expert medical AI analyzing photos for ALL types of health concerns including skin conditions, injuries, fractures, muscle tears, joint problems, and any other visible medical issues. Provide a comprehensive analysis.

IMPORTANT: Consider all types of medical conditions - dermatological, orthopedic, soft tissue injuries, vascular issues, inflammatory conditions, traumatic injuries, etc.

Analyze the image and provide:
1. PRIMARY ASSESSMENT: Most likely condition based on visual evidence (be specific - e.g., "grade 2 ankle sprain" not just "ankle injury")
2. CONFIDENCE: Your confidence level (0-100%)
3. VISUAL OBSERVATIONS: What you specifically see (color, texture, size, deformity, swelling patterns)
4. DIFFERENTIAL DIAGNOSIS: Other possible conditions this could be
5. RECOMMENDATIONS: Clear next steps including when to seek medical care
6. RED FLAGS: Any urgent concerns requiring immediate medical attention
7. TRACKABLE METRICS: Measurable aspects that can be tracked over time

Format your response as JSON:
{
  "primary_assessment": "string",
  "confidence": number,
  "visual_observations": ["string"],
  "differential_diagnosis": ["string"],
  "recommendations": ["string"],
  "red_flags": ["string"],
  "trackable_metrics": [
    {
      "metric_name": "string",
      "current_value": number,
      "unit": "string",
      "suggested_tracking": "daily|weekly|monthly"
    }
  ]
}

Be thorough and consider all medical possibilities. Use your advanced reasoning to provide accurate analysis.

CRITICAL: Output ONLY valid JSON with no text before or after. Do not include markdown formatting or code blocks."""

PHOTO_COMPARISON_PROMPT = """Compare these medical photos taken at different times. Analyze:

1. SIZE CHANGES: Measure or estimate size differences
2. COLOR CHANGES: Note any color evolution
3. TEXTURE CHANGES: Surface characteristics
4. OVERALL TREND: Is it improving, worsening, or stable?
5. SPECIFIC OBSERVATIONS: Notable changes

Consider all types of conditions - skin issues, injuries, swelling, etc.

Format as JSON:
{
  "days_between": number,
  "changes": {
    "size": { "from": number, "to": number, "unit": "string", "change": number },
    "color": { "description": "string" },
    "texture": { "description": "string" }
  },
  "trend": "improving|worsening|stable",
  "ai_summary": "string"
}

CRITICAL: Output ONLY valid JSON with no text before or after. Do not include markdown formatting or code blocks."""


async def file_to_base64(file: UploadFile) -> str:
    """Convert uploaded file to base64 string"""
    contents = await file.read()
    return base64.b64encode(contents).decode('utf-8')


async def validate_photo_upload(file: UploadFile) -> Dict[str, Any]:
    """Validate uploaded photo file"""
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}")
    
    # Reset file pointer after validation
    await file.seek(0)
    
    return {"valid": True, "size": file.size, "mime_type": file.content_type}


async def call_openrouter(model: str, messages: List[Dict], max_tokens: int = 1000, temperature: float = 0.3) -> Dict:
    """Make API call to OpenRouter"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'HTTP-Referer': os.getenv('APP_URL', 'http://localhost:3000'),
                'X-Title': 'Proxima-1 Photo Analysis'
            },
            json={
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=180.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"OpenRouter API error: {response.text}")
        
        return response.json()


@router.post("/categorize", response_model=PhotoCategorizeResponse)
async def categorize_photo(
    photo: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """Categorize a photo using Mistral model"""
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    # Validate file
    await validate_photo_upload(photo)
    
    # Convert to base64
    base64_image = await file_to_base64(photo)
    
    # Call Mistral for categorization
    try:
        response = await call_openrouter(
            model='mistralai/mistral-small-3.1-24b-instruct',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': PHOTO_CATEGORIZATION_PROMPT},
                    {'type': 'image_url', 'image_url': {'url': f'data:{photo.content_type};base64,{base64_image}'}}
                ]
            }],
            max_tokens=100,
            temperature=0.1
        )
        
        # Parse response
        content = response['choices'][0]['message']['content']
        categorization = extract_json_from_text(content)
        
        # Add session context if provided
        if session_id and supabase:
            session = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
            if session.data:
                photo_count = supabase.table('photo_uploads').select('id').eq('session_id', session_id).execute()
                categorization['session_context'] = {
                    'is_sensitive_session': session.data.get('is_sensitive', False),
                    'previous_photos': len(photo_count.data) if photo_count.data else 0
                }
        
        return categorization
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")


class CreateSessionRequest(BaseModel):
    user_id: str
    condition_name: str
    description: Optional[str] = None

@router.post("/sessions")
async def create_photo_session(request: CreateSessionRequest):
    """Create a new photo session"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Debug logging
    print(f"Session creation request: user_id={request.user_id}, condition={request.condition_name}")
    
    # Validate input (model already validates required fields)
    if not request.user_id:
        raise HTTPException(status_code=422, detail="user_id is required")
    if not request.condition_name:
        raise HTTPException(status_code=422, detail="condition_name is required")
    
    try:
        session_result = supabase.table('photo_sessions').insert({
            'user_id': request.user_id,
            'condition_name': request.condition_name,
            'description': request.description
        }).execute()
        
        if not session_result.data:
            print(f"Session creation failed - no data returned")
            raise HTTPException(status_code=500, detail="Failed to create session - no data returned")
        
        return {
            'session_id': session_result.data[0]['id'],
            'condition_name': request.condition_name,
            'created_at': session_result.data[0]['created_at']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")

@router.post("/upload", response_model=PhotoUploadResponse)
async def upload_photos(
    photos: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    condition_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user_id: str = Form(...)
):
    """Upload and process multiple photos"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    if len(photos) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos per upload")
    
    # Create or get session
    # Check if session_id is a temporary one or doesn't exist in DB
    session_exists = False
    if session_id and not session_id.startswith('temp-'):
        # Verify session exists in database
        existing_session = supabase.table('photo_sessions').select('id').eq('id', session_id).single().execute()
        session_exists = existing_session.data is not None
    
    if not session_exists:
        # Need to create a new session
        if not condition_name:
            raise HTTPException(status_code=400, detail="condition_name required when creating new session")
        
        session_result = supabase.table('photo_sessions').insert({
            'user_id': user_id,
            'condition_name': condition_name,
            'description': description
        }).execute()
        
        session_id = session_result.data[0]['id']
    
    uploaded_photos = []
    requires_action = {'type': None, 'affected_photos': [], 'message': None}
    
    for photo in photos:
        # Validate
        await validate_photo_upload(photo)
        
        # Categorize
        base64_image = await file_to_base64(photo)
        
        try:
            response = await call_openrouter(
                model='mistralai/mistral-small-3.1-24b-instruct',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': PHOTO_CATEGORIZATION_PROMPT},
                        {'type': 'image_url', 'image_url': {'url': f'data:{photo.content_type};base64,{base64_image}'}}
                    ]
                }],
                max_tokens=100,
                temperature=0.1
            )
            
            content = response['choices'][0]['message']['content']
            categorization = extract_json_from_text(content)
            category = categorization['category']
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")
        
        # Handle based on category
        stored = False
        storage_url = None
        photo_id = str(uuid.uuid4())
        
        if category in ['medical_normal', 'medical_gore']:
            # Upload to Supabase Storage
            sanitized_filename = sanitize_filename(photo.filename)
            file_name = f"{user_id}/{session_id}/{datetime.now().timestamp()}_{sanitized_filename}"
            
            try:
                # Reset file pointer
                await photo.seek(0)
                file_data = await photo.read()
                
                upload_response = supabase.storage.from_(STORAGE_BUCKET).upload(
                    file_name,
                    file_data,
                    file_options={"content-type": photo.content_type}
                )
                
                storage_url = file_name
                stored = True
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")
                
        elif category == 'medical_sensitive':
            # Mark session as sensitive
            supabase.table('photo_sessions').update({
                'is_sensitive': True
            }).eq('id', session_id).execute()
            
            # For sensitive photos, store the base64 data in the database temporarily
            await photo.seek(0)  # Reset file pointer
            photo_data = await photo.read()
            base64_data = base64.b64encode(photo_data).decode('utf-8')
            
            # Store base64 in temporary_data field
            stored = False  # Mark as not stored in permanent storage
            
            requires_action['type'] = 'sensitive_modal'
            requires_action['affected_photos'].append(photo_id)
            requires_action['message'] = 'Sensitive content detected. Photos will be analyzed temporarily without permanent storage.'
            
        elif category == 'unclear':
            requires_action['type'] = 'unclear_modal'
            requires_action['affected_photos'].append(photo_id)
            requires_action['message'] = 'Photo quality insufficient for analysis.'
            
        elif category == 'inappropriate':
            raise HTTPException(status_code=400, detail='Inappropriate content detected')
        
        # Save upload record
        upload_data = {
            'id': photo_id,
            'session_id': session_id,
            'category': category,
            'storage_url': storage_url,
            'file_metadata': {
                'size': photo.size,
                'mime_type': photo.content_type,
                'original_name': photo.filename
            }
        }
        
        # Add temporary base64 data for sensitive photos
        if category == 'medical_sensitive':
            upload_data['temporary_data'] = base64_data
            
        upload_record = supabase.table('photo_uploads').insert(upload_data).execute()
        
        # Get preview URL if stored
        preview_url = None
        if stored:
            try:
                preview_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                    storage_url,
                    3600  # 1 hour expiry
                )
                preview_url = preview_data.get('signedURL') or preview_data.get('signedUrl')
            except Exception as e:
                print(f"Error creating preview URL: {str(e)}")
                preview_url = None
        
        uploaded_photos.append({
            'id': photo_id,
            'category': category,
            'stored': stored,
            'preview_url': preview_url
        })
    
    # Update session last_photo_at
    supabase.table('photo_sessions').update({
        'last_photo_at': datetime.now().isoformat()
    }).eq('id', session_id).execute()
    
    return {
        'session_id': session_id,
        'uploaded_photos': uploaded_photos,
        'requires_action': requires_action if requires_action['type'] else None
    }


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photos(request: PhotoAnalysisRequest):
    """Analyze photos using GPT-4V"""
    print(f"Analyze request received - session_id: {request.session_id}, photo_ids: {request.photo_ids}")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    # Get photos
    photos_result = supabase.table('photo_uploads').select('*').in_('id', request.photo_ids).execute()
    
    if not photos_result.data:
        print(f"No photos found for IDs: {request.photo_ids}")
        raise HTTPException(status_code=404, detail="Photos not found")
    
    photos = photos_result.data
    print(f"Found {len(photos)} photos to analyze")
    
    # Get session
    session_result = supabase.table('photo_sessions').select('*').eq('id', request.session_id).single().execute()
    if not session_result.data:
        print(f"Session {request.session_id} not found")
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_result.data
    
    # Build photo content for AI
    photo_contents = []
    
    for photo in photos:
        if photo['storage_url']:
            # Get from storage
            try:
                download_response = supabase.storage.from_(STORAGE_BUCKET).download(photo['storage_url'])
                
                # Handle different response types from Supabase
                if hasattr(download_response, 'content'):
                    # Response object with content attribute
                    file_data = download_response.content
                elif isinstance(download_response, bytes):
                    # Direct bytes response
                    file_data = download_response
                elif hasattr(download_response, 'read'):
                    # File-like object
                    file_data = download_response.read()
                elif isinstance(download_response, dict) and 'data' in download_response:
                    # Dict response with data key
                    file_data = download_response['data']
                else:
                    # Log the actual type for debugging
                    print(f"Unknown download response type: {type(download_response)}")
                    print(f"Response dir: {dir(download_response)}")
                    # Try to get data attribute
                    file_data = getattr(download_response, 'data', download_response)
                
                if not isinstance(file_data, bytes):
                    print(f"Error: file_data is not bytes, got {type(file_data)}")
                    # Try to convert to bytes if possible
                    if hasattr(file_data, 'encode'):
                        file_data = file_data.encode()
                    else:
                        raise TypeError(f"Cannot convert {type(file_data)} to bytes")
                
                base64_image = base64.b64encode(file_data).decode('utf-8')
                
            except Exception as e:
                print(f"Error downloading photo {photo['id']}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")
        else:
            # For sensitive photos, check if we have temporary_data
            if photo.get('temporary_data'):
                # Use the base64 data directly
                base64_image = photo['temporary_data']
            else:
                # No data available
                print(f"No storage URL or temporary data for photo {photo['id']}")
                raise HTTPException(status_code=400, detail="Cannot analyze photo without data")
        
        # Get proper mime type from file metadata or default to jpeg
        mime_type = photo.get('file_metadata', {}).get('mime_type', 'image/jpeg')
        photo_contents.append({
            'type': 'image_url',
            'image_url': {'url': f'data:{mime_type};base64,{base64_image}'}
        })
    
    # Build analysis prompt
    analysis_prompt = PHOTO_ANALYSIS_PROMPT
    if request.context:
        analysis_prompt += f"\n\nUser context: {request.context}"
    
    # Call O4-mini for analysis
    import time
    start_time = time.time()
    try:
        print(f"Starting AI analysis at {datetime.now()}")
        response = await call_openrouter(
            model='google/gemini-2.5-pro',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': analysis_prompt},
                    *photo_contents
                ]
            }],
            max_tokens=2000,
            temperature=0.1
        )
        
        elapsed = time.time() - start_time
        print(f"AI response received after {elapsed:.1f} seconds")
        
        content = response['choices'][0]['message']['content']
        print(f"AI response content: {content[:500]}...")  # Log first 500 chars
        analysis = extract_json_from_text(content)
        print(f"Extracted analysis: {analysis}")
        
        # Ensure all expected fields exist as arrays
        if not isinstance(analysis.get('visual_observations'), list):
            analysis['visual_observations'] = [str(analysis.get('visual_observations', 'No observations'))]
        if not isinstance(analysis.get('differential_diagnosis'), list):
            analysis['differential_diagnosis'] = [str(analysis.get('differential_diagnosis', 'No differential diagnosis'))]
        if not isinstance(analysis.get('recommendations'), list):
            analysis['recommendations'] = [str(analysis.get('recommendations', 'Consult a healthcare provider'))]
        if not isinstance(analysis.get('red_flags'), list):
            analysis['red_flags'] = []
        if not isinstance(analysis.get('trackable_metrics'), list):
            analysis['trackable_metrics'] = []
        
    except Exception as e:
        print(f"Primary model failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
        try:
            print("Falling back to gemini-2.0-flash-exp:free")
            response = await call_openrouter(
                model='google/gemini-2.0-flash-exp:free',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': analysis_prompt},
                        *photo_contents
                    ]
                }],
                max_tokens=2000,
                temperature=0.1
            )
            
            content = response['choices'][0]['message']['content']
            analysis = extract_json_from_text(content)
            
            # Ensure all expected fields exist as arrays (same as above)
            if not isinstance(analysis.get('visual_observations'), list):
                analysis['visual_observations'] = [str(analysis.get('visual_observations', 'No observations'))]
            if not isinstance(analysis.get('differential_diagnosis'), list):
                analysis['differential_diagnosis'] = [str(analysis.get('differential_diagnosis', 'No differential diagnosis'))]
            if not isinstance(analysis.get('recommendations'), list):
                analysis['recommendations'] = [str(analysis.get('recommendations', 'Consult a healthcare provider'))]
            if not isinstance(analysis.get('red_flags'), list):
                analysis['red_flags'] = []
            if not isinstance(analysis.get('trackable_metrics'), list):
                analysis['trackable_metrics'] = []
            
        except Exception as e2:
            print(f"Fallback model also failed: {str(e2)}")
            print(f"Error type: {type(e2).__name__}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e2)}")
    
    # Handle comparison if requested
    comparison = None
    if request.comparison_photo_ids and len(request.comparison_photo_ids) > 0:
        # Get comparison photos
        comp_photos_result = supabase.table('photo_uploads').select('*').in_('id', request.comparison_photo_ids).execute()
        
        if comp_photos_result.data:
            # Build comparison prompt
            comp_contents = []
            for photo in comp_photos_result.data:
                if photo['storage_url']:
                    try:
                        download_response = supabase.storage.from_(STORAGE_BUCKET).download(photo['storage_url'])
                        
                        # Handle different response types from Supabase
                        if hasattr(download_response, 'content'):
                            file_data = download_response.content
                        elif isinstance(download_response, bytes):
                            file_data = download_response
                        elif hasattr(download_response, 'read'):
                            file_data = download_response.read()
                        elif isinstance(download_response, dict) and 'data' in download_response:
                            file_data = download_response['data']
                        else:
                            file_data = getattr(download_response, 'data', download_response)
                        
                        if not isinstance(file_data, bytes):
                            print(f"Error: file_data is not bytes, got {type(file_data)}")
                            # Try to convert to bytes if possible
                            if hasattr(file_data, 'encode'):
                                file_data = file_data.encode()
                            else:
                                raise TypeError(f"Cannot convert {type(file_data)} to bytes")
                        
                        base64_image = base64.b64encode(file_data).decode('utf-8')
                        comp_contents.append({
                            'type': 'image_url',
                            'image_url': {'url': f'data:image/jpeg;base64,{base64_image}'}
                        })
                    except Exception as e:
                        print(f"Error downloading comparison photo: {str(e)}")
                        # Continue without this comparison photo
                        continue
            
            # Call AI for comparison
            try:
                comp_response = await call_openrouter(
                    model='google/gemini-2.5-pro',
                    messages=[{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': PHOTO_COMPARISON_PROMPT},
                            *photo_contents,
                            {'type': 'text', 'text': 'COMPARED TO:'},
                            *comp_contents
                        ]
                    }],
                    max_tokens=1000,
                    temperature=0.1
                )
                
                comp_content = comp_response['choices'][0]['message']['content']
                comparison = extract_json_from_text(comp_content)
                
            except Exception as e:
                # Comparison is optional, so just log error
                print(f"Comparison failed: {str(e)}")
    
    # Save analysis
    analysis_record = supabase.table('photo_analyses').insert({
        'session_id': request.session_id,
        'photo_ids': request.photo_ids,
        'analysis_data': analysis,
        'model_used': 'google/gemini-2.5-pro',
        'confidence_score': analysis.get('confidence', 0),
        'is_sensitive': session.get('is_sensitive', False) or request.temporary_analysis,
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat() if request.temporary_analysis else None
    }).execute()
    
    analysis_id = analysis_record.data[0]['id']
    
    # Generate tracking suggestions if applicable
    if analysis.get('trackable_metrics') and not request.temporary_analysis:
        for metric in analysis['trackable_metrics']:
            supabase.table('photo_tracking_suggestions').insert({
                'session_id': request.session_id,
                'analysis_id': analysis_id,
                'metric_suggestions': [metric]
            }).execute()
    
    return {
        'analysis_id': analysis_id,
        'analysis': analysis,
        'comparison': comparison,
        'expires_at': analysis_record.data[0].get('expires_at')
    }


@router.get("/sessions")
async def get_photo_sessions(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(20, description="Number of sessions to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get user's photo sessions"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Get sessions
    sessions_result = supabase.table('photo_sessions').select('*').eq('user_id', user_id).order('created_at.desc').range(offset, offset + limit - 1).execute()
    
    sessions = []
    for session in sessions_result.data:
        # Get photo count
        photo_count_result = supabase.table('photo_uploads').select('id').eq('session_id', session['id']).execute()
        photo_count = len(photo_count_result.data) if photo_count_result.data else 0
        
        # Get analysis count
        analysis_count_result = supabase.table('photo_analyses').select('id').eq('session_id', session['id']).execute()
        analysis_count = len(analysis_count_result.data) if analysis_count_result.data else 0
        
        # Get latest analysis summary
        latest_analysis = None
        if analysis_count > 0:
            latest_result = supabase.table('photo_analyses').select('analysis_data').eq('session_id', session['id']).order('created_at.desc').limit(1).execute()
            if latest_result.data and latest_result.data[0]['analysis_data']:
                latest_analysis = latest_result.data[0]['analysis_data'].get('primary_assessment')
        
        # Get thumbnail
        thumbnail_url = None
        if photo_count > 0:
            first_photo = supabase.table('photo_uploads').select('storage_url').eq('session_id', session['id']).eq('category', 'medical_normal').limit(1).execute()
            if first_photo.data and first_photo.data[0]['storage_url']:
                try:
                    thumb_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                        first_photo.data[0]['storage_url'],
                        3600
                    )
                    thumbnail_url = thumb_data.get('signedURL') or thumb_data.get('signedUrl')
                except Exception as e:
                    print(f"Error creating thumbnail URL: {str(e)}")
                    thumbnail_url = None
        
        sessions.append({
            'id': session['id'],
            'condition_name': session['condition_name'],
            'created_at': session['created_at'],
            'last_photo_at': session.get('last_photo_at'),
            'photo_count': photo_count,
            'analysis_count': analysis_count,
            'is_sensitive': session.get('is_sensitive', False),
            'latest_summary': latest_analysis,
            'thumbnail_url': thumbnail_url
        })
    
    # Get total count
    total_result = supabase.table('photo_sessions').select('id', count='exact').eq('user_id', user_id).execute()
    total = total_result.count
    
    return {
        'sessions': sessions,
        'total': total,
        'has_more': (offset + limit) < total
    }


@router.get("/session/{session_id}")
async def get_photo_session_detail(session_id: str):
    """Get detailed session information"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Get session
    session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
    
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Get photos
    photos_result = supabase.table('photo_uploads').select('*').eq('session_id', session_id).order('uploaded_at').execute()
    
    photos = []
    for photo in photos_result.data:
        photo_data = {
            'id': photo['id'],
            'category': photo['category'],
            'uploaded_at': photo['uploaded_at'],
            'preview_url': None
        }
        
        if photo['storage_url']:
            try:
                preview_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                    photo['storage_url'],
                    3600
                )
                photo_data['preview_url'] = preview_data.get('signedURL') or preview_data.get('signedUrl')
            except Exception as e:
                print(f"Error creating preview URL for session detail: {str(e)}")
                photo_data['preview_url'] = None
        
        photos.append(photo_data)
    
    # Get analyses
    analyses_result = supabase.table('photo_analyses').select('*').eq('session_id', session_id).order('created_at.desc').execute()
    
    analyses = []
    for analysis in analyses_result.data:
        analyses.append({
            'id': analysis['id'],
            'created_at': analysis['created_at'],
            'primary_assessment': analysis['analysis_data'].get('primary_assessment') if analysis['analysis_data'] else None,
            'confidence': analysis.get('confidence_score', 0),
            'expires_at': analysis.get('expires_at')
        })
    
    return {
        'session': session,
        'photos': photos,
        'analyses': analyses
    }


@router.delete("/session/{session_id}")
async def delete_photo_session(session_id: str):
    """Soft delete a photo session"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Update session
    supabase.table('photo_sessions').update({
        'deleted_at': datetime.now().isoformat()
    }).eq('id', session_id).execute()
    
    # Mark photos as deleted
    supabase.table('photo_uploads').update({
        'deleted_at': datetime.now().isoformat()
    }).eq('session_id', session_id).execute()
    
    return {'message': 'Session deleted successfully'}


@router.post("/tracking/approve")
async def approve_tracking_suggestions(
    analysis_id: str,
    metric_configs: List[Dict[str, Any]]
):
    """Approve and create tracking configurations from photo analysis"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Get analysis
    analysis_result = supabase.table('photo_analyses').select('*').eq('id', analysis_id).single().execute()
    
    if not analysis_result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analysis_result.data
    
    # Create tracking configurations
    tracking_configs = []
    
    for config in metric_configs:
        # Create tracking configuration
        tracking_result = supabase.table('photo_tracking_configurations').insert({
            'user_id': analysis['user_id'],
            'session_id': analysis['session_id'],
            'metric_name': config['metric_name'],
            'y_axis_label': config['y_axis_label'],
            'y_axis_min': config.get('y_axis_min', 0),
            'y_axis_max': config.get('y_axis_max', 100),
            'created_from': 'photo_analysis',
            'source_id': analysis_id
        }).execute()
        
        tracking_configs.append({
            'id': tracking_result.data[0]['id'],
            'metric_name': config['metric_name'],
            'configuration_id': tracking_result.data[0]['id']
        })
        
        # Add initial data point if provided
        if 'initial_value' in config:
            supabase.table('photo_tracking_data').insert({
                'configuration_id': tracking_result.data[0]['id'],
                'value': config['initial_value'],
                'analysis_id': analysis_id
            }).execute()
    
    return {
        'tracking_configs': tracking_configs,
        'dashboard_url': '/dashboard#tracking'
    }