"""Photo Analysis API endpoints"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Query, Response
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
    PhotoSessionResponse,
    PhotoAnalysisReportRequest,
    PhotoReminderConfigureRequest,
    PhotoMonitoringSuggestRequest
)
from utils.json_parser import extract_json_from_text

router = APIRouter(prefix="/api/photo-analysis", tags=["photo-analysis"])

import re
import asyncio
from typing import Tuple

class SmartPhotoBatcher:
    """Intelligently select photos for comparison when total exceeds limit"""
    
    def __init__(self, max_photos: int = 40):
        self.max_photos = max_photos
        self.reserved_recent = 5  # Always include last 5 photos
        self.reserved_baseline = 1  # Always include first photo
        
    def select_photos_for_comparison(
        self, 
        all_photos: List[Dict], 
        all_analyses: Optional[List[Dict]] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Select most relevant photos for comparison
        Returns: (selected_photos, selection_info)
        """
        if len(all_photos) <= self.max_photos:
            return all_photos, {
                "total_photos": len(all_photos),
                "photos_shown": len(all_photos),
                "selection_method": "all_photos",
                "omitted_periods": []
            }
        
        selected = []
        selection_info = {
            "total_photos": len(all_photos),
            "photos_shown": self.max_photos,
            "selection_reasoning": [],
            "omitted_periods": []
        }
        
        # Sort photos by date
        sorted_photos = sorted(all_photos, key=lambda x: x.get('uploaded_at', ''))
        
        # Phase 1: Always include first photo (baseline)
        if sorted_photos:
            selected.append(sorted_photos[0])
            selection_info["selection_reasoning"].append("Included baseline (first) photo")
        
        # Phase 2: Always include most recent photos
        recent_photos = sorted_photos[-self.reserved_recent:]
        selected.extend(recent_photos)
        selection_info["selection_reasoning"].append(f"Included {len(recent_photos)} most recent photos")
        
        # Phase 3: Fill remaining slots intelligently
        remaining_slots = self.max_photos - len(selected)
        middle_photos = sorted_photos[1:-self.reserved_recent] if len(sorted_photos) > self.reserved_recent + 1 else []
        
        if middle_photos and remaining_slots > 0:
            # Calculate importance scores
            scored_photos = []
            for i, photo in enumerate(middle_photos):
                score = self._calculate_photo_importance(photo, i, middle_photos, all_analyses)
                scored_photos.append((score, photo))
            
            # Sort by score and take top photos
            scored_photos.sort(key=lambda x: x[0], reverse=True)
            selected_middle = [photo for score, photo in scored_photos[:remaining_slots]]
            
            # Insert in chronological order
            for photo in sorted(selected_middle, key=lambda x: x.get('uploaded_at', '')):
                # Find correct position to maintain chronological order
                insert_pos = 1  # After baseline
                for i in range(1, len(selected) - len(recent_photos)):
                    if selected[i].get('uploaded_at', '') > photo.get('uploaded_at', ''):
                        break
                    insert_pos = i + 1
                selected.insert(insert_pos, photo)
            
            selection_info["selection_reasoning"].append(
                f"Selected {len(selected_middle)} photos from middle period based on importance"
            )
        
        # Calculate omitted periods
        selection_info["omitted_periods"] = self._calculate_omitted_periods(sorted_photos, selected)
        
        return selected, selection_info
    
    def _calculate_photo_importance(
        self, 
        photo: Dict, 
        index: int, 
        all_middle_photos: List[Dict],
        all_analyses: Optional[List[Dict]]
    ) -> float:
        """Calculate importance score for a photo"""
        score = 0.0
        
        # 1. Temporal distribution - prefer evenly spaced photos
        total_photos = len(all_middle_photos)
        ideal_spacing = total_photos / (self.max_photos - self.reserved_recent - self.reserved_baseline)
        distance_from_ideal = abs(index % ideal_spacing)
        temporal_score = 100 * (1 - distance_from_ideal / ideal_spacing)
        score += temporal_score
        
        # 2. Quality score if available
        if photo.get('quality_score'):
            score += photo['quality_score'] * 0.5
        
        # 3. Check if photo has associated analysis with significant findings
        if all_analyses:
            photo_analysis = next(
                (a for a in all_analyses if photo['id'] in a.get('photo_ids', [])), 
                None
            )
            if photo_analysis:
                # High confidence changes
                if photo_analysis.get('confidence_score', 0) < 70:
                    score += 50  # Uncertain cases are important
                
                # Red flags present
                if photo_analysis.get('analysis_data', {}).get('red_flags'):
                    score += 100
                
                # Marked as significant change in comparison
                if photo_analysis.get('comparison', {}).get('trend') == 'worsening':
                    score += 80
        
        # 4. User notes or follow-up flag
        if photo.get('followup_notes'):
            score += 75
        
        return score
    
    def _calculate_omitted_periods(
        self, 
        all_photos: List[Dict], 
        selected_photos: List[Dict]
    ) -> List[Dict]:
        """Calculate time periods that were omitted from selection"""
        omitted_periods = []
        selected_dates = {p['uploaded_at'][:10] for p in selected_photos}
        
        current_gap_start = None
        for i, photo in enumerate(all_photos):
            photo_date = photo['uploaded_at'][:10]
            
            if photo_date not in selected_dates:
                if current_gap_start is None:
                    current_gap_start = photo_date
            else:
                if current_gap_start is not None:
                    # Gap ended
                    prev_photo_date = all_photos[i-1]['uploaded_at'][:10] if i > 0 else current_gap_start
                    omitted_periods.append({
                        "start": current_gap_start,
                        "end": prev_photo_date,
                        "photos_omitted": sum(
                            1 for p in all_photos 
                            if current_gap_start <= p['uploaded_at'][:10] <= prev_photo_date
                        )
                    })
                    current_gap_start = None
        
        return omitted_periods


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


async def call_openrouter_with_retry(model: str, messages: List[Dict], max_tokens: int = 1000, 
                                   temperature: float = 0.3, max_retries: int = 3) -> Dict:
    """Make API call to OpenRouter with retry logic"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await call_openrouter(model, messages, max_tokens, temperature)
        except HTTPException as e:
            last_error = e
            # Check if it's a rate limit error
            if e.status_code == 429:
                # For rate limit errors, wait longer
                wait_time = min(10 * (attempt + 1), 30)  # 10s, 20s, 30s max
                print(f"Rate limit hit (429), waiting {wait_time}s before retry...")
                # Try a different model on rate limit
                if attempt == 0:
                    if model == 'openai/gpt-5':
                        print("Switching to google/gemini-2.5-pro due to rate limit")
                        model = 'google/gemini-2.5-pro'
                    elif model == 'google/gemini-2.5-pro':
                        print("Switching to gemini-2.0-flash-exp:free due to rate limit")
                        model = 'google/gemini-2.0-flash-exp:free'
            else:
                # Regular exponential backoff for other errors
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff for non-HTTP errors
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
    
    raise last_error

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


@router.get("/session/{session_id}/follow-up/test")
async def test_follow_up_route(session_id: str):
    """Test endpoint to verify routing works"""
    return {
        "status": "ok",
        "session_id": session_id,
        "endpoint": "follow-up test"
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
  "subcategory": "specific_condition_type (e.g., 'dermatological_rash', 'orthopedic_fracture', 'vascular_varicose')",
  "quality_score": 85
}"""

PHOTO_ANALYSIS_PROMPT = """You are an expert medical AI analyzing photos. 

FIRST STEP - QUESTION DETECTION:
Check if the user's description contains a question that needs answering.
Questions can be:
- Direct questions: "Is this serious?", "What is this?", "Should I see a doctor?", "Does this look normal?"
- Implied questions: "I'm worried about...", "I'm not sure if...", "Could this be...", "I wonder if..."
- Comparative questions: "Is this getting worse?", "Has this improved?", "Is it bigger than before?"
- Concern expressions: "This looks concerning", "I'm scared about this", "Is this dangerous?"

IF A QUESTION IS DETECTED:
- Set question_detected to true
- Provide a direct, specific answer in question_answer field addressing their concern
- The answer should be reassuring when appropriate but always medically accurate
- Continue with standard analysis

SECOND STEP - VISUAL ANALYSIS:
Focus on what's VISUALLY OBSERVABLE and MEASURABLE over time. Be specific with estimates even without measuring tools.

Analyze and provide:
1. PRIMARY ASSESSMENT: Most specific diagnosis possible based on visual evidence
2. CONFIDENCE: Your confidence level (0-100%)
3. KEY OBSERVATIONS: Most important visual findings that could change over time
4. TRACKABLE FEATURES: Identify the 3-5 most important things to monitor for THIS specific condition

For measurements, estimate using visual cues:
- Size: Compare to common references (fingernail ~10mm, penny ~20mm, etc)
- Colors: Describe precisely (e.g., "dark brown center, light brown periphery")
- Changes: What specific visual features would indicate improvement/worsening

Format your response as JSON:
{
  "question_detected": boolean,
  "question_answer": "Direct, specific answer to the user's question" (ONLY include this field if question_detected is true),
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
  ],
  "key_measurements": {
    "size_estimate_mm": number,
    "size_reference": "string",
    "primary_color": "descriptive string",
    "secondary_colors": ["string"],
    "texture_description": "string",
    "symmetry_observation": "string",
    "elevation_observation": "string"
  },
  "condition_insights": {
    "most_important_features": ["string"],
    "progression_indicators": {
      "improvement_signs": ["string"],
      "worsening_signs": ["string"],
      "stability_signs": ["string"]
    },
    "optimal_photo_angle": "string",
    "optimal_lighting": "string"
  },
  "urgency_level": "low|medium|high|urgent",
  "follow_up_timing": "string"
}

IMPORTANT: Focus on what YOU can see and track visually. Don't force measurements that aren't possible from the image.

CRITICAL: Output ONLY valid JSON with no text before or after."""

PHOTO_COMPARISON_PROMPT = """Compare these medical photos to identify the most important changes. Focus on what matters most for tracking this specific condition.

IMPORTANT: You will receive photos in two groups:
1. FIRST GROUP (before "COMPARED TO:"): These are the NEW/CURRENT photos taken most recently
2. SECOND GROUP (after "COMPARED TO:"): These are the PREVIOUS/BASELINE photos taken earlier

Analyze what has VISUALLY CHANGED from the PREVIOUS photos to the NEW photos:
1. Most significant change observed
2. Rate of change (rapid/gradual/stable)
3. Clinical significance of changes
4. What to monitor next

Provide specific observations comparing OLD to NEW:
- Size: "Increased from fingernail-sized to penny-sized" (not just "bigger")
- Color: "Center darkened from light brown to dark brown"
- Shape: "Border became more irregular on left side"
- Texture: "Surface went from smooth to rough with scaling"

Format as JSON:
{
  "days_between": number,
  "primary_change": "string - the MOST important change",
  "change_significance": "minor|moderate|significant|critical",
  "visual_changes": {
    "size": {
      "description": "string",
      "estimated_change_percent": number,
      "clinical_relevance": "string"
    },
    "color": {
      "description": "string", 
      "areas_affected": ["string"],
      "concerning": boolean
    },
    "shape": {
      "description": "string",
      "symmetry_change": "string",
      "border_changes": ["string"]
    },
    "texture": {
      "description": "string",
      "new_features": ["string"]
    }
  },
  "progression_analysis": {
    "overall_trend": "improving|stable|worsening|mixed",
    "confidence_in_trend": number,
    "rate_of_change": "rapid|moderate|slow|stable",
    "key_finding": "string"
  },
  "clinical_interpretation": "string - what these changes mean medically",
  "next_monitoring": {
    "focus_areas": ["string"],
    "red_flags_to_watch": ["string"],
    "optimal_interval_days": number
  }
}

CRITICAL: Output ONLY valid JSON with no text before or after."""


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
    
    # Call Gemini Flash Lite for faster categorization with retry
    try:
        response = await call_openrouter_with_retry(
            model='google/gemini-2.5-flash-lite',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': PHOTO_CATEGORIZATION_PROMPT},
                    {'type': 'image_url', 'image_url': {'url': f'data:{photo.content_type};base64,{base64_image}'}}
                ]
            }],
            max_tokens=50,
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
                model='google/gemini-2.5-flash-lite',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': PHOTO_CATEGORIZATION_PROMPT},
                        {'type': 'image_url', 'image_url': {'url': f'data:{photo.content_type};base64,{base64_image}'}}
                    ]
                }],
                max_tokens=50,
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
    
    # Build analysis prompt with user's description for question detection
    analysis_prompt = PHOTO_ANALYSIS_PROMPT
    if request.context:
        analysis_prompt += f"\n\nUser's description/question: {request.context}"
    
    # Call Gemini for analysis with retry
    import time
    start_time = time.time()
    try:
        print(f"Starting AI analysis at {datetime.now()}")
        # Try GPT-5 first, fallback to Gemini
        try:
            response = await call_openrouter_with_retry(
                model='openai/gpt-5',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': analysis_prompt},
                        *photo_contents
                    ]
                }],
                max_tokens=6000,  # Increased 3x for more detailed analysis
                temperature=0.1,
                max_retries=2  # Fewer retries for primary model
            )
        except Exception as e:
            print(f"GPT-5 failed, falling back to Gemini: {e}")
            response = await call_openrouter_with_retry(
                model='google/gemini-2.5-pro',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': analysis_prompt},
                        *photo_contents
                    ]
                }],
                max_tokens=6000,
                temperature=0.1,
                max_retries=3
            )
        
        elapsed = time.time() - start_time
        print(f"AI response received after {elapsed:.1f} seconds")
        
        content = response['choices'][0]['message']['content']
        print(f"AI response content: {content[:500]}...")  # Log first 500 chars
        analysis = extract_json_from_text(content)
        print(f"Extracted analysis: {analysis}")
        
        # Check if JSON extraction failed
        if analysis is None:
            raise ValueError(f"Failed to parse JSON from AI response. Content: {content[:1000]}")
        
        # Log if a question was detected
        if analysis.get('question_detected'):
            print(f"✓ Question detected! Answer: {analysis.get('question_answer', 'No answer provided')[:200]}...")
        
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
            response = await call_openrouter_with_retry(
                model='google/gemini-2.0-flash-exp:free',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': analysis_prompt},
                        *photo_contents
                    ]
                }],
                max_tokens=4000,  # Increased 2x for fallback model
                temperature=0.1,
                max_retries=2  # Fewer retries for fallback
            )
            
            content = response['choices'][0]['message']['content']
            analysis = extract_json_from_text(content)
            
            # Check if JSON extraction failed
            if analysis is None:
                raise ValueError(f"Failed to parse JSON from fallback AI response. Content: {content[:1000]}")
            
            # Log if a question was detected in fallback
            if analysis.get('question_detected'):
                print(f"✓ Question detected (fallback)! Answer: {analysis.get('question_answer', 'No answer')[:200]}...")
            
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
            # IMPORTANT: Photo order matters for accurate progression analysis:
            # 1. NEW photos (photo_contents) are sent FIRST - these are the current/latest photos
            # 2. PREVIOUS photos (comp_contents) are sent SECOND - these are the baseline/older photos
            # The AI analyzes changes FROM old TO new to determine progression
            try:
                # Try GPT-5 first for comparison
                try:
                    comp_response = await call_openrouter(
                        model='openai/gpt-5',
                        messages=[{
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': PHOTO_COMPARISON_PROMPT},
                                *photo_contents,  # NEW photos (current state)
                                {'type': 'text', 'text': '--- COMPARED TO PREVIOUS/BASELINE PHOTOS BELOW ---'},
                                *comp_contents   # PREVIOUS photos (baseline)
                            ]
                        }],
                        max_tokens=3000,  # Increased 3x for detailed comparisons
                        temperature=0.1
                    )
                except Exception as e:
                    print(f"GPT-5 failed for comparison, using Gemini: {e}")
                    comp_response = await call_openrouter(
                        model='google/gemini-2.5-pro',
                        messages=[{
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': PHOTO_COMPARISON_PROMPT},
                                *photo_contents,  # NEW photos (current state)
                                {'type': 'text', 'text': '--- COMPARED TO PREVIOUS/BASELINE PHOTOS BELOW ---'},
                                *comp_contents   # PREVIOUS photos (baseline)
                            ]
                        }],
                        max_tokens=3000,
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
        'model_used': 'openai/gpt-5',  # Updated to reflect primary model
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


@router.post("/reports/photo-analysis")
async def generate_photo_analysis_report(request: PhotoAnalysisReportRequest):
    """Generate comprehensive report from photo analyses"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    print(f"Generating photo analysis report for sessions: {request.session_ids}")
    
    # Verify user owns all sessions
    sessions_result = supabase.table('photo_sessions')\
        .select('*')\
        .in_('id', request.session_ids)\
        .eq('user_id', request.user_id)\
        .execute()
    
    if not sessions_result.data or len(sessions_result.data) != len(request.session_ids):
        raise HTTPException(status_code=404, detail="One or more sessions not found or unauthorized")
    
    sessions = sessions_result.data
    
    # Get all analyses for these sessions
    analyses_result = supabase.table('photo_analyses')\
        .select('*')\
        .in_('session_id', request.session_ids)\
        .order('created_at.desc')\
        .execute()
    
    analyses = analyses_result.data or []
    
    # Get all photos for visual timeline (non-sensitive only)
    photos_result = supabase.table('photo_uploads')\
        .select('*')\
        .in_('session_id', request.session_ids)\
        .neq('category', 'medical_sensitive')\
        .order('uploaded_at')\
        .execute()
    
    photos = photos_result.data or []
    
    # Apply time range filter if specified
    if request.time_range_days:
        cutoff_date = (datetime.now() - timedelta(days=request.time_range_days)).isoformat()
        analyses = [a for a in analyses if a['created_at'] >= cutoff_date]
        photos = [p for p in photos if p['uploaded_at'] >= cutoff_date]
    
    # Get tracking data if requested
    tracking_data = {}
    if request.include_tracking_data:
        # Get photo tracking configurations
        tracking_configs_result = supabase.table('photo_tracking_configurations')\
            .select('*')\
            .in_('session_id', request.session_ids)\
            .execute()
        
        for config in (tracking_configs_result.data or []):
            # Get data points
            data_points_result = supabase.table('photo_tracking_data')\
                .select('*')\
                .eq('configuration_id', config['id'])\
                .order('recorded_at')\
                .execute()
            
            tracking_data[config['metric_name']] = {
                'config': config,
                'data_points': data_points_result.data or []
            }
    
    # Build comprehensive report data
    report_data = {
        'sessions': sessions,
        'total_analyses': len(analyses),
        'total_photos': len(photos),
        'date_range': {
            'start': min([a['created_at'] for a in analyses]) if analyses else None,
            'end': max([a['created_at'] for a in analyses]) if analyses else None
        },
        'conditions_tracked': [s['condition_name'] for s in sessions],
        'analyses_timeline': [],
        'visual_progression': [],
        'tracking_metrics': tracking_data,
        'ai_insights': {}
    }
    
    # Build analyses timeline
    for analysis in analyses:
        report_data['analyses_timeline'].append({
            'date': analysis['created_at'],
            'primary_assessment': analysis['analysis_data'].get('primary_assessment'),
            'confidence': analysis['confidence_score'],
            'key_observations': analysis['analysis_data'].get('visual_observations', [])[:3],
            'recommendations': analysis['analysis_data'].get('recommendations', [])[:2]
        })
    
    # Build visual progression (for non-sensitive photos)
    if request.include_visual_timeline and photos:
        for photo in photos:
            if photo['storage_url']:
                try:
                    # Create signed URL
                    url_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                        photo['storage_url'],
                        3600  # 1 hour
                    )
                    preview_url = url_data.get('signedURL') or url_data.get('signedUrl')
                    
                    # Find associated analysis
                    photo_analysis = next(
                        (a for a in analyses if photo['id'] in a.get('photo_ids', [])),
                        None
                    )
                    
                    report_data['visual_progression'].append({
                        'date': photo['uploaded_at'],
                        'preview_url': preview_url,
                        'category': photo['category'],
                        'assessment': photo_analysis['analysis_data'].get('primary_assessment') if photo_analysis else None
                    })
                except Exception as e:
                    print(f"Error creating preview URL: {str(e)}")
    
    # Generate AI insights using all the data
    insights_prompt = f"""Analyze this comprehensive photo-based health tracking data and provide insights:

Conditions tracked: {', '.join(report_data['conditions_tracked'])}
Total analyses: {report_data['total_analyses']}
Date range: {report_data['date_range']['start']} to {report_data['date_range']['end']}

Recent assessments:
{json.dumps(report_data['analyses_timeline'][:5], indent=2)}

Tracking metrics:
{json.dumps({k: len(v['data_points']) for k, v in tracking_data.items()}, indent=2)}

Provide:
1. Overall progression summary (improving/stable/worsening)
2. Key patterns identified
3. Most significant changes
4. Recommendations for continued tracking
5. When to seek medical attention

Format as JSON:
{{
  "overall_trend": "improving|stable|worsening",
  "confidence": 0-100,
  "key_patterns": ["pattern1", "pattern2"],
  "significant_changes": ["change1", "change2"],
  "tracking_recommendations": ["rec1", "rec2"],
  "medical_attention_indicators": ["indicator1", "indicator2"],
  "summary": "1-2 sentence summary"
}}"""
    
    try:
        # Try GPT-5 first, fallback to Gemini
        try:
            response = await call_openrouter_with_retry(
                model='openai/gpt-5',
                messages=[
                    {"role": "system", "content": "You are a medical AI analyzing photo-based health tracking data."},
                    {"role": "user", "content": insights_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
        except Exception as e:
            print(f"GPT-5 failed for insights, using Gemini: {e}")
            response = await call_openrouter_with_retry(
                model='google/gemini-2.5-pro',
                messages=[
                    {"role": "system", "content": "You are a medical AI analyzing photo-based health tracking data."},
                    {"role": "user", "content": insights_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
        
        insights = extract_json_from_text(response['choices'][0]['message']['content'])
        report_data['ai_insights'] = insights
        
    except Exception as e:
        print(f"Error generating AI insights: {str(e)}")
        report_data['ai_insights'] = {
            "error": "Could not generate AI insights",
            "summary": "Please review the timeline data manually"
        }
    
    # Create report record
    report_id = str(uuid.uuid4())
    report_record = {
        'id': report_id,
        'user_id': request.user_id,
        'report_type': 'photo_analysis',
        'report_data': report_data,
        'created_at': datetime.now().isoformat(),
        'session_ids': request.session_ids
    }
    
    # Save to medical_reports table
    supabase.table('medical_reports').insert(report_record).execute()
    
    return {
        'report_id': report_id,
        'report_type': 'photo_analysis',
        'generated_at': report_record['created_at'],
        'report_data': report_data,
        'status': 'success'
    }


@router.post("/session/{session_id}/follow-up")
async def add_follow_up_photos(
    session_id: str,
    photos: List[UploadFile] = File(...),
    auto_compare: bool = Form(True),
    notes: Optional[str] = Form(None),
    compare_with_photo_ids: Optional[str] = Form(None)  # JSON string of photo IDs
):
    """Add follow-up photos to an existing session and optionally compare with previous photos"""
    try:
        print(f"Follow-up endpoint called for session {session_id}")
        print(f"Number of photos: {len(photos) if photos else 0}")
        print(f"Auto compare: {auto_compare}")
        print(f"Notes: {notes}")
        print(f"Compare with IDs: {compare_with_photo_ids}")
        
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection not configured")
        if not OPENROUTER_API_KEY:
            raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
        
        if len(photos) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 photos per follow-up upload")
        
        # Verify session exists
        session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_result.data
        user_id = session['user_id']
        
        # Parse compare_with_photo_ids if provided
        comparison_photo_ids = []
        if compare_with_photo_ids:
            try:
                comparison_photo_ids = json.loads(compare_with_photo_ids)
            except json.JSONDecodeError:
                comparison_photo_ids = []
    
        # Get previous photos for comparison if auto_compare is true and no specific IDs provided
        smart_batching_info = None
        if auto_compare and not comparison_photo_ids:
            # Get ALL photos from this session for smart selection
            all_prev_photos_result = supabase.table('photo_uploads')\
                .select('*')\
                .eq('session_id', session_id)\
                .eq('category', 'medical_normal')\
                .order('uploaded_at')\
                .execute()
            
            if all_prev_photos_result.data:
                # Use smart batching if there are many photos
                batcher = SmartPhotoBatcher(max_photos=40)
                
                # Get analyses for importance scoring
                analyses_result = supabase.table('photo_analyses')\
                    .select('*')\
                    .eq('session_id', session_id)\
                    .execute()
                
                selected_photos, smart_batching_info = batcher.select_photos_for_comparison(
                    all_prev_photos_result.data,
                    analyses_result.data if analyses_result.data else None
                )
                
                comparison_photo_ids = [p['id'] for p in selected_photos]
                print(f"Smart batching selected {len(comparison_photo_ids)} photos from {len(all_prev_photos_result.data)} total")
        
        # Process and upload new photos
        uploaded_photos = []
        
        for photo in photos:
            # Validate
            await validate_photo_upload(photo)
            
            # Categorize
            base64_image = await file_to_base64(photo)
            
            try:
                response = await call_openrouter_with_retry(
                    model='google/gemini-2.5-flash-lite',
                    messages=[{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': PHOTO_CATEGORIZATION_PROMPT},
                            {'type': 'image_url', 'image_url': {'url': f'data:{photo.content_type};base64,{base64_image}'}}
                        ]
                    }],
                    max_tokens=50,
                    temperature=0.1
                )
                
                content = response['choices'][0]['message']['content']
                categorization = extract_json_from_text(content)
                category = categorization['category']
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")
            
            # Upload based on category
            stored = False
            storage_url = None
            photo_id = str(uuid.uuid4())
            
            if category in ['medical_normal', 'medical_gore']:
                # Upload to storage
                sanitized_filename = sanitize_filename(photo.filename)
                file_name = f"{user_id}/{session_id}/followup_{datetime.now().timestamp()}_{sanitized_filename}"
                
                try:
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
                # Store base64 temporarily
                await photo.seek(0)
                photo_data = await photo.read()
                base64_data = base64.b64encode(photo_data).decode('utf-8')
                stored = False
            
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
                },
                'is_followup': True,
                'followup_notes': notes
            }
            
            if category == 'medical_sensitive':
                upload_data['temporary_data'] = base64_data
            
            upload_record = supabase.table('photo_uploads').insert(upload_data).execute()
            
            # Get preview URL
            preview_url = None
            if stored:
                try:
                    preview_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                        storage_url,
                        3600
                    )
                    preview_url = preview_data.get('signedURL') or preview_data.get('signedUrl')
                except Exception as e:
                    print(f"Error creating preview URL: {str(e)}")
            
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
        
        # Perform comparison if requested
        comparison_results = None
        if comparison_photo_ids and uploaded_photos:
            # Analyze new photos with comparison
            new_photo_ids = [p['id'] for p in uploaded_photos]
            
            analysis_request = PhotoAnalysisRequest(
                session_id=session_id,
                photo_ids=new_photo_ids,
                comparison_photo_ids=comparison_photo_ids,
                context=f"Follow-up photos. Notes: {notes}" if notes else "Follow-up photos"
            )
            
            try:
                analysis_response = await analyze_photos(analysis_request)
                
                # Calculate days since last photo
                if comparison_photo_ids:
                    prev_photo = supabase.table('photo_uploads')\
                        .select('uploaded_at')\
                        .eq('id', comparison_photo_ids[0])\
                        .single()\
                        .execute()
                    
                    if prev_photo.data:
                        prev_date = datetime.fromisoformat(prev_photo.data['uploaded_at'].replace('Z', '+00:00'))
                        days_since = (datetime.now(prev_date.tzinfo) - prev_date).days
                    else:
                        days_since = None
                else:
                    days_since = None
                
                comparison_results = {
                    'compared_with': comparison_photo_ids,
                    'days_since_last': days_since,
                    'analysis': {
                        'trend': analysis_response.get('comparison', {}).get('trend', 'unknown'),
                        'changes': analysis_response.get('comparison', {}).get('changes', {}),
                        'confidence': analysis_response.get('analysis', {}).get('confidence', 0) / 100,
                        'summary': analysis_response.get('comparison', {}).get('ai_summary', "No comparison available")
                    },
                    'visual_comparison': {
                        'primary_change': analysis_response.get('comparison', {}).get('primary_change'),
                        'change_significance': analysis_response.get('comparison', {}).get('change_significance'),
                        'visual_changes': analysis_response.get('comparison', {}).get('visual_changes', {}),
                        'progression_analysis': analysis_response.get('comparison', {}).get('progression_analysis', {}),
                        'clinical_interpretation': analysis_response.get('comparison', {}).get('clinical_interpretation'),
                        'next_monitoring': analysis_response.get('comparison', {}).get('next_monitoring', {})
                    },
                    'key_measurements': {
                        'latest': analysis_response.get('analysis', {}).get('key_measurements', {}),
                        'condition_insights': analysis_response.get('analysis', {}).get('condition_insights', {})
                    }
                }
            except Exception as e:
                print(f"Comparison failed: {str(e)}")
                comparison_results = {
                    'error': 'Comparison failed',
                    'message': str(e)
                }
        
        # Generate follow-up suggestions using full history
        # Get all analyses for this session to make intelligent suggestions
        all_analyses = supabase.table('photo_analyses')\
            .select('*')\
            .eq('session_id', session_id)\
            .order('created_at')\
            .execute()
        
        all_photos = supabase.table('photo_uploads')\
            .select('*')\
            .eq('session_id', session_id)\
            .order('uploaded_at')\
            .execute()
        
        follow_up_suggestion = await generate_intelligent_follow_up_suggestion(
            session, 
            all_analyses.data if all_analyses.data else [],
            all_photos.data if all_photos.data else [],
            analysis_response.get('analysis') if 'analysis_response' in locals() and isinstance(analysis_response, dict) else None
        )
        
        return {
            'uploaded_photos': uploaded_photos,
            'comparison_results': comparison_results,
            'follow_up_suggestion': follow_up_suggestion,
            'smart_batching_info': smart_batching_info  # Include batching info if photos were intelligently selected
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as they already have proper error structure
        raise
        
    except Exception as e:
        print(f"Unexpected error in follow-up photos: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )


async def generate_intelligent_follow_up_suggestion(
    session: Dict, 
    all_analyses: List[Dict],
    all_photos: List[Dict],
    latest_analysis: Optional[Dict]
) -> Dict:
    """Generate intelligent follow-up suggestions based on full session history"""
    
    # Calculate progression metrics from history
    progression_data = analyze_progression_history(all_analyses)
    
    # Base interval on multiple factors
    suggested_interval = calculate_optimal_interval(
        session,
        progression_data,
        latest_analysis,
        len(all_photos)
    )
    
    # Determine priority based on actual data
    priority = determine_priority(progression_data, latest_analysis)
    
    # Generate intelligent reasoning
    reasoning = generate_contextual_reasoning(
        session,
        progression_data,
        suggested_interval,
        priority
    )
    
    return {
        'benefits_from_tracking': True,
        'suggested_interval_days': suggested_interval,
        'reasoning': reasoning,
        'priority': priority,
        'progression_summary': progression_data,
        'adaptive_scheduling': {
            'current_phase': progression_data.get('phase', 'monitoring'),
            'next_interval': suggested_interval,
            'adjust_based_on': progression_data.get('key_factors', [])
        }
    }


def analyze_progression_history(analyses: List[Dict]) -> Dict:
    """Analyze historical progression from all analyses"""
    if not analyses:
        return {
            'trend': 'unknown',
            'rate_of_change': 'unknown',
            'phase': 'initial',
            'confidence_trend': []
        }
    
    # Extract trends from analyses
    trends = []
    confidences = []
    red_flag_count = 0
    
    for analysis in analyses:
        data = analysis.get('analysis_data', {})
        if data:
            confidences.append(analysis.get('confidence_score', 0))
            if data.get('red_flags'):
                red_flag_count += len(data.get('red_flags', []))
    
    # Determine overall trend
    if len(analyses) >= 2:
        recent_trend = 'stable'
        # Check comparisons for trends
        for analysis in analyses[-3:]:  # Last 3 analyses
            if analysis.get('comparison', {}).get('trend') == 'worsening':
                recent_trend = 'worsening'
                break
            elif analysis.get('comparison', {}).get('trend') == 'improving':
                recent_trend = 'improving'
    else:
        recent_trend = 'initial'
    
    # Calculate rate of change
    if len(analyses) >= 2:
        first_date = datetime.fromisoformat(analyses[0]['created_at'].replace('Z', '+00:00'))
        last_date = datetime.fromisoformat(analyses[-1]['created_at'].replace('Z', '+00:00'))
        days_span = (last_date - first_date).days
        changes_per_week = len(analyses) / max(days_span / 7, 1)
        
        if changes_per_week > 2:
            rate = 'rapid'
        elif changes_per_week > 0.5:
            rate = 'moderate'
        else:
            rate = 'slow'
    else:
        rate = 'unknown'
    
    return {
        'trend': recent_trend,
        'rate_of_change': rate,
        'total_analyses': len(analyses),
        'red_flags_total': red_flag_count,
        'confidence_trend': confidences,
        'phase': determine_monitoring_phase(len(analyses), recent_trend),
        'key_factors': identify_key_factors(analyses)
    }


def calculate_optimal_interval(
    session: Dict,
    progression_data: Dict,
    latest_analysis: Optional[Dict],
    photo_count: int
) -> int:
    """Calculate optimal follow-up interval based on multiple factors"""
    
    base_interval = 14  # Default 2 weeks
    
    # Adjust based on trend
    if progression_data['trend'] == 'worsening':
        base_interval = 3
    elif progression_data['trend'] == 'improving':
        base_interval = 21
    elif progression_data['trend'] == 'initial':
        base_interval = 7
    
    # Adjust based on rate of change
    if progression_data['rate_of_change'] == 'rapid':
        base_interval = max(base_interval // 2, 2)
    elif progression_data['rate_of_change'] == 'slow':
        base_interval = min(base_interval * 1.5, 30)
    
    # Adjust based on red flags
    if progression_data['red_flags_total'] > 0:
        base_interval = min(base_interval, 7)
    
    # Adjust based on monitoring phase
    if progression_data['phase'] == 'active_monitoring':
        base_interval = min(base_interval, 7)
    elif progression_data['phase'] == 'maintenance':
        base_interval = max(base_interval, 30)
    
    # Consider latest analysis findings
    if latest_analysis:
        if latest_analysis.get('next_monitoring', {}).get('optimal_interval_days'):
            ai_suggested = latest_analysis['next_monitoring']['optimal_interval_days']
            # Average with calculated interval
            base_interval = (base_interval + ai_suggested) // 2
    
    return int(base_interval)


def determine_priority(progression_data: Dict, latest_analysis: Optional[Dict]) -> str:
    """Determine follow-up priority based on data"""
    
    if progression_data['red_flags_total'] > 0:
        return 'urgent'
    
    if progression_data['trend'] == 'worsening':
        return 'important'
    
    if progression_data['rate_of_change'] == 'rapid':
        return 'important'
    
    if latest_analysis and latest_analysis.get('change_significance') == 'critical':
        return 'urgent'
    
    return 'routine'


def generate_contextual_reasoning(
    session: Dict,
    progression_data: Dict,
    interval: int,
    priority: str
) -> str:
    """Generate intelligent reasoning for the suggestion"""
    
    condition = session.get('condition_name', 'condition')
    
    reasons = []
    
    # Add trend-based reasoning
    if progression_data['trend'] == 'worsening':
        reasons.append(f"Recent analyses show worsening trend for {condition}")
    elif progression_data['trend'] == 'improving':
        reasons.append(f"Positive improvement trend observed")
    elif progression_data['trend'] == 'initial':
        reasons.append(f"Initial monitoring phase for new {condition}")
    
    # Add rate-based reasoning
    if progression_data['rate_of_change'] == 'rapid':
        reasons.append("Rapid changes detected requiring close monitoring")
    elif progression_data['rate_of_change'] == 'slow':
        reasons.append("Stable progression allows for extended intervals")
    
    # Add priority reasoning
    if priority == 'urgent':
        reasons.append("Urgent follow-up recommended due to concerning findings")
    elif priority == 'important':
        reasons.append("Important to maintain regular monitoring")
    
    # Add interval reasoning
    reasons.append(f"Based on {progression_data['total_analyses']} previous analyses, {interval}-day interval is optimal")
    
    return ". ".join(reasons)


def determine_monitoring_phase(analysis_count: int, trend: str) -> str:
    """Determine what phase of monitoring we're in"""
    if analysis_count <= 2:
        return 'initial'
    elif analysis_count <= 5 and trend != 'stable':
        return 'active_monitoring'
    elif trend == 'stable' and analysis_count > 5:
        return 'maintenance'
    else:
        return 'ongoing'


def identify_key_factors(analyses: List[Dict]) -> List[str]:
    """Identify key factors affecting monitoring"""
    factors = []
    
    if not analyses:
        return ['Initial assessment needed']
    
    # Check for volatility
    trends = []
    for analysis in analyses:
        if analysis.get('comparison', {}).get('trend'):
            trends.append(analysis['comparison']['trend'])
    
    if len(set(trends)) > 1:
        factors.append('Variable progression pattern')
    
    # Check for red flags
    has_red_flags = any(
        a.get('analysis_data', {}).get('red_flags') 
        for a in analyses
    )
    if has_red_flags:
        factors.append('Red flags present')
    
    # Check confidence levels
    low_confidence = any(
        a.get('confidence_score', 100) < 70 
        for a in analyses
    )
    if low_confidence:
        factors.append('Uncertain findings requiring validation')
    
    return factors


# Keep the old function for backward compatibility
async def generate_follow_up_suggestion(session: Dict, latest_photo: Optional[Dict]) -> Dict:
    """Legacy function - redirects to intelligent version with minimal data"""
    return await generate_intelligent_follow_up_suggestion(session, [], [], None)


@router.post("/reminders/configure")
async def configure_photo_reminders(request: PhotoReminderConfigureRequest):
    """Configure follow-up reminders for a photo analysis session"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    print(f"Configuring reminders for session {request.session_id}, analysis {request.analysis_id}")
    
    # Verify session exists and user owns it
    session_result = supabase.table('photo_sessions').select('*').eq('id', request.session_id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Verify analysis exists
    analysis_result = supabase.table('photo_analyses').select('*').eq('id', request.analysis_id).single().execute()
    if not analysis_result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analysis_result.data
    
    # Generate AI reasoning for the reminder interval
    ai_reasoning = await generate_reminder_reasoning(
        session['condition_name'],
        analysis['analysis_data'],
        request.interval_days
    )
    
    # Check if reminder already exists
    existing_reminder = supabase.table('photo_reminders')\
        .select('*')\
        .eq('session_id', request.session_id)\
        .single()\
        .execute()
    
    # Calculate next reminder date
    next_reminder_date = None
    if request.enabled:
        next_reminder_date = (datetime.now() + timedelta(days=request.interval_days)).isoformat()
    
    reminder_data = {
        'session_id': request.session_id,
        'analysis_id': request.analysis_id,
        'user_id': session['user_id'],
        'enabled': request.enabled,
        'interval_days': request.interval_days,
        'reminder_method': request.reminder_method,
        'reminder_text': request.reminder_text,
        'contact_info': request.contact_info,
        'next_reminder_date': next_reminder_date,
        'ai_reasoning': ai_reasoning,
        'last_sent_at': None,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    if existing_reminder.data:
        # Update existing reminder
        reminder_id = existing_reminder.data['id']
        supabase.table('photo_reminders')\
            .update({
                **reminder_data,
                'created_at': existing_reminder.data['created_at']  # Preserve original creation date
            })\
            .eq('id', reminder_id)\
            .execute()
    else:
        # Create new reminder
        reminder_id = str(uuid.uuid4())
        reminder_data['id'] = reminder_id
        supabase.table('photo_reminders').insert(reminder_data).execute()
    
    return {
        'reminder_id': reminder_id,
        'session_id': request.session_id,
        'next_reminder_date': next_reminder_date,
        'interval_days': request.interval_days,
        'method': request.reminder_method,
        'status': 'active' if request.enabled else 'disabled',
        'ai_reasoning': ai_reasoning,
        'can_modify': True
    }


async def generate_reminder_reasoning(condition_name: str, analysis_data: Dict, interval_days: int) -> str:
    """Generate AI reasoning for the reminder interval"""
    primary_assessment = analysis_data.get('primary_assessment', '')
    
    # Provide context-specific reasoning
    if interval_days <= 3:
        return f"Frequent monitoring recommended for {condition_name}. Short intervals help detect rapid changes."
    elif interval_days <= 7:
        return f"Weekly monitoring for {primary_assessment} allows tracking of treatment response and progression."
    elif interval_days <= 30:
        return f"Monthly checks for {condition_name} provide good balance between monitoring and convenience."
    else:
        return f"Extended monitoring interval suitable for stable conditions like {primary_assessment}."


@router.post("/monitoring/suggest")
async def suggest_monitoring_plan(request: PhotoMonitoringSuggestRequest):
    """Get AI-powered monitoring suggestions based on analysis results"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    print(f"Generating monitoring suggestions for analysis {request.analysis_id}")
    
    # Get analysis data
    analysis_result = supabase.table('photo_analyses')\
        .select('*')\
        .eq('id', request.analysis_id)\
        .single()\
        .execute()
    
    if not analysis_result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analysis_result.data
    
    # Get session data
    session_result = supabase.table('photo_sessions')\
        .select('*')\
        .eq('id', analysis['session_id'])\
        .single()\
        .execute()
    
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Build prompt for AI monitoring suggestions
    monitoring_prompt = f"""Based on this medical photo analysis, provide a monitoring plan:

Condition: {session['condition_name']}
Primary Assessment: {analysis['analysis_data'].get('primary_assessment', 'Unknown')}
Confidence: {analysis['analysis_data'].get('confidence', 0)}%
Visual Observations: {', '.join(analysis['analysis_data'].get('visual_observations', [])[:3])}
Red Flags: {', '.join(analysis['analysis_data'].get('red_flags', []))}

Context from user:
{json.dumps(request.condition_context) if request.condition_context else 'No additional context'}

Provide a detailed monitoring plan including:
1. Recommended interval in days for photo follow-ups
2. Whether intervals should be fixed or change over time
3. Specific schedule for the next 6 months
4. What changes to watch for
5. When to seek immediate medical attention

Format as JSON:
{{
  "monitoring_plan": {{
    "recommended_interval_days": number,
    "interval_type": "fixed|decreasing|conditional",
    "reasoning": "detailed explanation",
    "schedule": [
      {{"check_number": 1, "days_from_now": number, "purpose": "string"}},
      ...
    ],
    "red_flags_to_watch": ["specific change 1", "specific change 2"],
    "when_to_see_doctor": "specific guidance"
  }},
  "confidence": 0.0-1.0,
  "based_on_conditions": ["condition type 1", "condition type 2"]
}}"""
    
    try:
        # Use GPT-5 for medical reasoning, with Gemini fallback
        try:
            response = await call_openrouter_with_retry(
                model='openai/gpt-5',
                messages=[
                    {"role": "system", "content": "You are a medical AI specializing in visual monitoring of health conditions."},
                    {"role": "user", "content": monitoring_prompt}
                ],
                max_tokens=4500,  # Increased 3x for detailed monitoring suggestions
                temperature=0.3
            )
        except Exception as e:
            print(f"GPT-5 failed for monitoring, using Gemini: {e}")
            response = await call_openrouter_with_retry(
                model='google/gemini-2.5-pro',
                messages=[
                    {"role": "system", "content": "You are a medical AI specializing in visual monitoring of health conditions."},
                    {"role": "user", "content": monitoring_prompt}
                ],
                max_tokens=4500,
                temperature=0.3
            )
        
        monitoring_data = extract_json_from_text(response['choices'][0]['message']['content'])
        
        # Ensure required fields exist
        if 'monitoring_plan' not in monitoring_data:
            monitoring_data = {'monitoring_plan': monitoring_data}
        
        plan = monitoring_data['monitoring_plan']
        
        # Validate and ensure all fields
        if 'recommended_interval_days' not in plan:
            plan['recommended_interval_days'] = 14
        if 'interval_type' not in plan:
            plan['interval_type'] = 'fixed'
        if 'schedule' not in plan or not isinstance(plan['schedule'], list):
            plan['schedule'] = generate_default_schedule(plan['recommended_interval_days'])
        if 'red_flags_to_watch' not in plan or not isinstance(plan['red_flags_to_watch'], list):
            plan['red_flags_to_watch'] = ['Rapid size increase', 'Color changes', 'New symptoms']
        
        return monitoring_data
        
    except Exception as e:
        print(f"Error generating monitoring suggestions: {str(e)}")
        # Return sensible defaults
        return {
            "monitoring_plan": {
                "recommended_interval_days": 14,
                "interval_type": "fixed",
                "reasoning": "Regular bi-weekly monitoring recommended for most conditions",
                "schedule": generate_default_schedule(14),
                "red_flags_to_watch": [
                    "Rapid changes in size or appearance",
                    "New pain or discomfort",
                    "Signs of infection"
                ],
                "when_to_see_doctor": "If you notice any rapid changes or concerning symptoms"
            },
            "confidence": 0.7,
            "based_on_conditions": ["general monitoring"]
        }


def generate_default_schedule(interval_days: int) -> List[Dict]:
    """Generate a default monitoring schedule"""
    schedule = []
    for i in range(1, 7):  # 6 check-ins
        schedule.append({
            "check_number": i,
            "days_from_now": interval_days * i,
            "purpose": f"Regular monitoring check #{i}"
        })
    return schedule


@router.get("/session/{session_id}/timeline")
async def get_session_timeline(session_id: str):
    """Get complete timeline of photos, analyses, and reminders for a session"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    print(f"Getting timeline for session {session_id}")
    
    # Get session data
    session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Get all photos for this session
    photos_result = supabase.table('photo_uploads')\
        .select('*')\
        .eq('session_id', session_id)\
        .order('uploaded_at')\
        .execute()
    
    photos = photos_result.data or []
    
    # Get all analyses
    analyses_result = supabase.table('photo_analyses')\
        .select('*')\
        .eq('session_id', session_id)\
        .order('created_at')\
        .execute()
    
    analyses = analyses_result.data or []
    
    # Get reminder configuration
    reminder_result = supabase.table('photo_reminders')\
        .select('*')\
        .eq('session_id', session_id)\
        .single()\
        .execute()
    
    reminder = reminder_result.data
    
    # Build timeline events
    timeline_events = []
    
    # Add photo upload events
    for i, photo_group in enumerate(group_photos_by_date(photos)):
        event = {
            'date': photo_group[0]['uploaded_at'],
            'type': 'follow_up' if i > 0 else 'photo_upload',
            'photos': []
        }
        
        # Add photo details
        for photo in photo_group:
            photo_detail = {
                'id': photo['id'],
                'category': photo['category'],
                'preview_url': None
            }
            
            # Get preview URL for non-sensitive photos
            if photo['storage_url'] and photo['category'] != 'medical_sensitive':
                try:
                    url_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                        photo['storage_url'],
                        3600
                    )
                    photo_detail['preview_url'] = url_data.get('signedURL') or url_data.get('signedUrl')
                except Exception as e:
                    print(f"Error creating preview URL: {str(e)}")
            
            event['photos'].append(photo_detail)
        
        # Find associated analysis
        event_analysis = find_analysis_for_photos([p['id'] for p in photo_group], analyses)
        if event_analysis:
            event['analysis_summary'] = event_analysis['analysis_data'].get('primary_assessment', 'Analysis completed')
            
            # Add comparison data for follow-ups
            if i > 0 and event_analysis.get('comparison'):
                prev_photos = [p for pg in group_photos_by_date(photos)[:i] for p in pg]
                if prev_photos:
                    days_since = calculate_days_between(prev_photos[-1]['uploaded_at'], photo_group[0]['uploaded_at'])
                    event['comparison'] = {
                        'days_since_previous': days_since,
                        'trend': event_analysis['comparison'].get('trend', 'unknown'),
                        'summary': event_analysis['comparison'].get('ai_summary', 'No comparison available')
                    }
        
        timeline_events.append(event)
    
    # Add scheduled reminder event if active
    if reminder and reminder['enabled'] and reminder['next_reminder_date']:
        next_date = datetime.fromisoformat(reminder['next_reminder_date'].replace('Z', '+00:00'))
        if next_date > datetime.now(next_date.tzinfo):
            timeline_events.append({
                'date': reminder['next_reminder_date'],
                'type': 'scheduled_reminder',
                'status': 'upcoming',
                'message': reminder['reminder_text']
            })
    
    # Sort timeline by date
    timeline_events.sort(key=lambda x: x['date'])
    
    # Calculate next action
    next_action = None
    if reminder and reminder['enabled']:
        next_date = datetime.fromisoformat(reminder['next_reminder_date'].replace('Z', '+00:00'))
        days_until = (next_date - datetime.now(next_date.tzinfo)).days
        next_action = {
            'type': 'photo_follow_up',
            'date': reminder['next_reminder_date'],
            'days_until': max(0, days_until)
        }
    
    # Calculate overall trend
    overall_trend = calculate_overall_trend(analyses)
    
    # Calculate total duration
    if photos:
        first_date = datetime.fromisoformat(photos[0]['uploaded_at'].replace('Z', '+00:00'))
        last_date = datetime.fromisoformat(photos[-1]['uploaded_at'].replace('Z', '+00:00'))
        total_days = (last_date - first_date).days
    else:
        total_days = 0
    
    return {
        'session': {
            'id': session['id'],
            'condition_name': session['condition_name'],
            'created_at': session['created_at'],
            'is_sensitive': session.get('is_sensitive', False)
        },
        'timeline_events': timeline_events,
        'next_action': next_action,
        'overall_trend': {
            'direction': overall_trend,
            'total_duration_days': total_days,
            'number_of_checks': len(set(p['uploaded_at'][:10] for p in photos))  # Unique days
        }
    }


def group_photos_by_date(photos: List[Dict]) -> List[List[Dict]]:
    """Group photos uploaded on the same day"""
    if not photos:
        return []
    
    groups = []
    current_group = [photos[0]]
    current_date = photos[0]['uploaded_at'][:10]  # Extract date part
    
    for photo in photos[1:]:
        photo_date = photo['uploaded_at'][:10]
        if photo_date == current_date:
            current_group.append(photo)
        else:
            groups.append(current_group)
            current_group = [photo]
            current_date = photo_date
    
    if current_group:
        groups.append(current_group)
    
    return groups


def find_analysis_for_photos(photo_ids: List[str], analyses: List[Dict]) -> Optional[Dict]:
    """Find the analysis that includes these photo IDs"""
    for analysis in analyses:
        if any(pid in analysis.get('photo_ids', []) for pid in photo_ids):
            return analysis
    return None


def calculate_days_between(date1_str: str, date2_str: str) -> int:
    """Calculate days between two ISO date strings"""
    date1 = datetime.fromisoformat(date1_str.replace('Z', '+00:00'))
    date2 = datetime.fromisoformat(date2_str.replace('Z', '+00:00'))
    return abs((date2 - date1).days)


def calculate_overall_trend(analyses: List[Dict]) -> str:
    """Calculate overall trend from multiple analyses"""
    if len(analyses) < 2:
        return 'insufficient_data'
    
    # Look at comparison data in recent analyses
    trends = []
    for analysis in analyses:
        if analysis.get('comparison') and analysis['comparison'].get('trend'):
            trends.append(analysis['comparison']['trend'])
    
    if not trends:
        return 'stable'
    
    # Count trend occurrences
    improving = trends.count('improving')
    worsening = trends.count('worsening')
    stable = trends.count('stable')
    
    # Determine overall trend
    if worsening > improving + stable:
        return 'worsening'
    elif improving > worsening + stable:
        return 'improving'
    else:
        return 'stable'


@router.get("/session/{session_id}/progression-analysis")
async def get_progression_analysis(session_id: str):
    """
    Advanced progression analysis with velocity calculations and predictive modeling
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    print(f"Generating progression analysis for session {session_id}")
    
    # Get session data
    session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Get all analyses with comparisons
    analyses_result = supabase.table('photo_analyses')\
        .select('*')\
        .eq('session_id', session_id)\
        .order('created_at')\
        .execute()
    
    analyses = analyses_result.data or []
    
    if len(analyses) < 2:
        return {
            "progression_metrics": {
                "status": "insufficient_data",
                "message": "Need at least 2 analyses for progression analysis"
            }
        }
    
    # Calculate velocity metrics
    velocity_data = calculate_progression_velocity(analyses)
    
    # Calculate risk indicators
    risk_indicators = calculate_risk_indicators(analyses)
    
    # Generate clinical insights
    clinical_insights = generate_clinical_insights(
        session,
        analyses,
        velocity_data,
        risk_indicators
    )
    
    # Create visualization data
    visualization_data = prepare_visualization_data(analyses)
    
    # Update session with latest progression summary
    supabase.table('photo_sessions').update({
        'last_progression_analysis': datetime.now().isoformat(),
        'progression_summary': {
            'overall_trend': velocity_data['overall_trend'],
            'current_phase': velocity_data['monitoring_phase'],
            'risk_level': risk_indicators['overall_risk_level']
        }
    }).eq('id', session_id).execute()
    
    return {
        "progression_metrics": {
            "velocity": velocity_data,
            "risk_indicators": risk_indicators,
            "clinical_thresholds": clinical_insights['thresholds'],
            "recommendations": clinical_insights['recommendations']
        },
        "visualization_data": visualization_data,
        "summary": clinical_insights['summary'],
        "next_steps": clinical_insights['next_steps']
    }


def calculate_progression_velocity(analyses: List[Dict]) -> Dict:
    """Calculate rate and acceleration of changes"""
    
    # Extract size measurements over time
    size_timeline = []
    for analysis in analyses:
        if analysis.get('analysis_data', {}).get('key_measurements', {}).get('size_estimate_mm'):
            size_timeline.append({
                'date': analysis['created_at'],
                'size_mm': analysis['analysis_data']['key_measurements']['size_estimate_mm'],
                'confidence': analysis.get('confidence_score', 0)
            })
    
    velocity_data = {
        'overall_trend': 'stable',
        'size_change_rate': None,
        'acceleration': None,
        'projected_size_30d': None,
        'monitoring_phase': 'ongoing'
    }
    
    if len(size_timeline) >= 2:
        # Calculate rate of change
        first = size_timeline[0]
        last = size_timeline[-1]
        
        first_date = datetime.fromisoformat(first['date'].replace('Z', '+00:00'))
        last_date = datetime.fromisoformat(last['date'].replace('Z', '+00:00'))
        days_elapsed = (last_date - first_date).days
        
        if days_elapsed > 0:
            size_change = last['size_mm'] - first['size_mm']
            rate_per_week = (size_change / days_elapsed) * 7
            
            velocity_data['size_change_rate'] = f"{rate_per_week:.2f}mm/week"
            
            # Calculate acceleration if we have 3+ points
            if len(size_timeline) >= 3:
                mid_point = size_timeline[len(size_timeline)//2]
                
                # First half rate
                mid_date = datetime.fromisoformat(mid_point['date'].replace('Z', '+00:00'))
                first_half_days = (mid_date - first_date).days
                first_half_change = mid_point['size_mm'] - first['size_mm']
                first_half_rate = first_half_change / max(first_half_days, 1)
                
                # Second half rate
                second_half_days = (last_date - mid_date).days
                second_half_change = last['size_mm'] - mid_point['size_mm']
                second_half_rate = second_half_change / max(second_half_days, 1)
                
                # Acceleration
                if first_half_rate < second_half_rate:
                    velocity_data['acceleration'] = 'increasing'
                elif first_half_rate > second_half_rate:
                    velocity_data['acceleration'] = 'decreasing'
                else:
                    velocity_data['acceleration'] = 'stable'
            
            # Project 30 days
            if rate_per_week != 0:
                projected_change_30d = (rate_per_week / 7) * 30
                velocity_data['projected_size_30d'] = f"{last['size_mm'] + projected_change_30d:.1f}mm"
            
            # Determine trend
            if size_change > 0.5:
                velocity_data['overall_trend'] = 'growing'
            elif size_change < -0.5:
                velocity_data['overall_trend'] = 'shrinking'
            else:
                velocity_data['overall_trend'] = 'stable'
    
    # Determine monitoring phase
    velocity_data['monitoring_phase'] = determine_monitoring_phase(
        len(analyses),
        velocity_data['overall_trend']
    )
    
    return velocity_data


def calculate_risk_indicators(analyses: List[Dict]) -> Dict:
    """Calculate risk indicators based on progression patterns"""
    
    risk_indicators = {
        'rapid_growth': False,
        'color_darkening': False,
        'border_irregularity_increase': False,
        'new_colors_appearing': False,
        'asymmetry_increasing': False,
        'overall_risk_level': 'low'
    }
    
    # Check for rapid growth
    for i in range(1, len(analyses)):
        prev = analyses[i-1]
        curr = analyses[i]
        
        # Check size increase
        if (prev.get('analysis_data', {}).get('key_measurements', {}).get('size_estimate_mm') and 
            curr.get('analysis_data', {}).get('key_measurements', {}).get('size_estimate_mm')):
            
            prev_size = prev['analysis_data']['key_measurements']['size_estimate_mm']
            curr_size = curr['analysis_data']['key_measurements']['size_estimate_mm']
            
            if prev_size > 0 and (curr_size - prev_size) / prev_size > 0.2:  # 20% increase
                risk_indicators['rapid_growth'] = True
        
        # Check for color changes
        if curr.get('comparison', {}).get('visual_changes', {}).get('color', {}).get('concerning'):
            risk_indicators['color_darkening'] = True
        
        # Check for new colors
        prev_colors = prev.get('analysis_data', {}).get('key_measurements', {}).get('secondary_colors', [])
        curr_colors = curr.get('analysis_data', {}).get('key_measurements', {}).get('secondary_colors', [])
        
        if len(curr_colors) > len(prev_colors):
            risk_indicators['new_colors_appearing'] = True
    
    # Check latest analysis for border/asymmetry
    if analyses:
        latest = analyses[-1]
        if latest.get('analysis_data', {}).get('condition_insights', {}).get('progression_indicators', {}).get('worsening_signs'):
            worsening_signs = latest['analysis_data']['condition_insights']['progression_indicators']['worsening_signs']
            
            if any('border' in sign.lower() for sign in worsening_signs):
                risk_indicators['border_irregularity_increase'] = True
            
            if any('asymmetr' in sign.lower() for sign in worsening_signs):
                risk_indicators['asymmetry_increasing'] = True
    
    # Calculate overall risk
    risk_count = sum([
        risk_indicators['rapid_growth'],
        risk_indicators['color_darkening'],
        risk_indicators['border_irregularity_increase'],
        risk_indicators['new_colors_appearing'],
        risk_indicators['asymmetry_increasing']
    ])
    
    if risk_count >= 3:
        risk_indicators['overall_risk_level'] = 'high'
    elif risk_count >= 1:
        risk_indicators['overall_risk_level'] = 'moderate'
    else:
        risk_indicators['overall_risk_level'] = 'low'
    
    return risk_indicators


def generate_clinical_insights(
    session: Dict,
    analyses: List[Dict],
    velocity_data: Dict,
    risk_indicators: Dict
) -> Dict:
    """Generate clinical insights based on progression data"""
    
    condition_name = session.get('condition_name', 'condition')
    
    insights = {
        'thresholds': {},
        'recommendations': [],
        'summary': '',
        'next_steps': []
    }
    
    # Set clinical thresholds based on condition type
    if 'mole' in condition_name.lower() or 'lesion' in condition_name.lower():
        insights['thresholds'] = {
            'concerning_size': '6mm',
            'rapid_growth_threshold': '20% in 30 days',
            'color_change_threshold': 'Any darkening or new colors'
        }
        
        # Check against thresholds
        latest_size = None
        if analyses:
            latest = analyses[-1]
            latest_size = latest.get('analysis_data', {}).get('key_measurements', {}).get('size_estimate_mm')
        
        if latest_size and latest_size >= 6:
            insights['recommendations'].append("Size exceeds 6mm - dermatologist evaluation recommended")
    
    # Generate recommendations based on risk
    if risk_indicators['overall_risk_level'] == 'high':
        insights['recommendations'].extend([
            "Multiple concerning changes detected",
            "Urgent dermatologist consultation recommended",
            "Document all changes carefully"
        ])
        insights['next_steps'] = [
            "Schedule dermatologist appointment within 1 week",
            "Bring all photo documentation",
            "Note any symptoms (itching, bleeding)"
        ]
    elif risk_indicators['overall_risk_level'] == 'moderate':
        insights['recommendations'].extend([
            "Some changes observed requiring attention",
            "Continue close monitoring",
            "Consider dermatologist consultation"
        ])
        insights['next_steps'] = [
            "Monitor every 7-14 days",
            "Watch for rapid changes",
            "Schedule routine dermatologist check"
        ]
    else:
        insights['recommendations'].extend([
            "Stable progression observed",
            "Continue routine monitoring",
            "Annual dermatologist check recommended"
        ])
        insights['next_steps'] = [
            "Continue monthly photos",
            "Note any new symptoms",
            "Maintain photo documentation"
        ]
    
    # Generate summary
    trend_text = velocity_data.get('overall_trend', 'stable')
    rate_text = velocity_data.get('size_change_rate', 'minimal change')
    
    insights['summary'] = (
        f"Analysis of {len(analyses)} photos shows {trend_text} progression "
        f"with {rate_text}. Risk level: {risk_indicators['overall_risk_level']}. "
        f"Monitoring phase: {velocity_data.get('monitoring_phase', 'ongoing')}."
    )
    
    return insights


def prepare_visualization_data(analyses: List[Dict]) -> Dict:
    """Prepare data for frontend visualization"""
    
    timeline_data = []
    
    for analysis in analyses:
        data_point = {
            'date': analysis['created_at'],
            'confidence': analysis.get('confidence_score', 0),
            'primary_assessment': analysis.get('analysis_data', {}).get('primary_assessment', ''),
            'metrics': {}
        }
        
        # Extract key metrics
        measurements = analysis.get('analysis_data', {}).get('key_measurements', {})
        if measurements.get('size_estimate_mm'):
            data_point['metrics']['size_mm'] = measurements['size_estimate_mm']
        
        # Extract risk indicators
        if analysis.get('analysis_data', {}).get('red_flags'):
            data_point['has_red_flags'] = True
            data_point['red_flag_count'] = len(analysis['analysis_data']['red_flags'])
        
        timeline_data.append(data_point)
    
    # Calculate trend lines
    size_values = [p['metrics'].get('size_mm') for p in timeline_data if p['metrics'].get('size_mm')]
    
    trend_lines = []
    if len(size_values) >= 2:
        # Simple linear regression for trend line
        x_values = list(range(len(size_values)))
        mean_x = sum(x_values) / len(x_values)
        mean_y = sum(size_values) / len(size_values)
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, size_values))
        denominator = sum((x - mean_x) ** 2 for x in x_values)
        
        if denominator != 0:
            slope = numerator / denominator
            intercept = mean_y - slope * mean_x
            
            trend_lines = [
                {'x': 0, 'y': intercept},
                {'x': len(size_values) - 1, 'y': intercept + slope * (len(size_values) - 1)}
            ]
    
    return {
        'timeline': timeline_data,
        'trend_lines': trend_lines,
        'metrics': {
            'size': {
                'values': size_values,
                'unit': 'mm',
                'label': 'Size'
            }
        }
    }


@router.get("/session/{session_id}/analysis-history")
async def get_analysis_history_endpoint(
    session_id: str,
    current_analysis_id: Optional[str] = Query(None)
):
    """
    Get complete analysis history for a session with photo URLs.
    
    This endpoint provides all analyses for timeline navigation and photo viewing.
    
    Args:
        session_id: The photo session ID
        current_analysis_id: Optional current analysis to highlight
        
    Returns:
        Complete analysis history with:
        - All analyses in chronological order
        - Signed photo URLs (24hr expiration)
        - Navigation metadata
        - Full analysis data for each entry
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
    # Get session info
    session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_result.data
    
    # Get all analyses for this session (chronological order)
    analyses_result = supabase.table('photo_analyses')\
        .select('*')\
        .eq('session_id', session_id)\
        .order('created_at', desc=False)\
        .execute()
    
    analyses = analyses_result.data if analyses_result.data else []
    
    # Get all photos for this session
    photos_result = supabase.table('photo_uploads')\
        .select('*')\
        .eq('session_id', session_id)\
        .order('uploaded_at', desc=False)\
        .execute()
    
    photos = photos_result.data if photos_result.data else []
    photos_by_id = {photo['id']: photo for photo in photos}
    
    # Build analysis entries with photo URLs
    analysis_entries = []
    current_index = None
    
    for idx, analysis in enumerate(analyses):
        # Get primary photo for this analysis
        photo_ids = analysis.get('photo_ids', [])
        primary_photo = None
        photo_url = None
        thumbnail_url = None
        
        if photo_ids and photo_ids[0] in photos_by_id:
            primary_photo = photos_by_id[photo_ids[0]]
            
            # Generate signed URLs for non-sensitive photos
            if primary_photo.get('storage_url') and primary_photo.get('category') != 'medical_sensitive':
                try:
                    # Full size photo URL (24 hour expiration)
                    url_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                        primary_photo['storage_url'],
                        86400  # 24 hours
                    )
                    photo_url = url_data.get('signedURL') or url_data.get('signedUrl')
                    
                    # For now, thumbnail is same as full photo (frontend can handle resizing)
                    thumbnail_url = photo_url
                    
                except Exception as e:
                    print(f"Error creating signed URL: {str(e)}")
        
        # Extract key metrics
        analysis_data = analysis.get('analysis_data', {})
        key_metrics = {}
        
        # Try to get size from different possible locations
        if 'key_measurements' in analysis_data:
            key_metrics['size_mm'] = analysis_data['key_measurements'].get('size_estimate_mm')
        elif 'trackable_metrics' in analysis_data:
            # Look for size metric in trackable metrics
            for metric in analysis_data.get('trackable_metrics', []):
                if 'size' in metric.get('metric_name', '').lower():
                    key_metrics['size_mm'] = metric.get('current_value')
                    break
        
        # Determine trend
        trend = 'unknown'
        if 'comparison' in analysis:
            trend = analysis['comparison'].get('trend', 'unknown')
        elif idx > 0:
            # Try to infer trend from confidence or other metrics
            prev_confidence = analyses[idx-1].get('confidence_score', 0)
            curr_confidence = analysis.get('confidence_score', 0)
            if curr_confidence > prev_confidence + 5:
                trend = 'improving'
            elif curr_confidence < prev_confidence - 5:
                trend = 'worsening'
            else:
                trend = 'stable'
        
        # Count red flags
        red_flags = analysis_data.get('red_flags', [])
        has_red_flags = len(red_flags) > 0
        red_flag_count = len(red_flags)
        
        # Determine urgency level based on red flags and recommendations
        urgency_level = 'low'
        if red_flag_count > 2:
            urgency_level = 'high'
        elif red_flag_count > 0:
            urgency_level = 'medium'
        elif any('urgent' in rec.lower() or 'immediate' in rec.lower() 
                for rec in analysis_data.get('recommendations', [])):
            urgency_level = 'high'
        
        entry = {
            'id': analysis['id'],
            'analysis_id': analysis['id'],  # Both for compatibility
            'date': analysis['created_at'],
            'photo_url': photo_url,
            'thumbnail_url': thumbnail_url,
            'primary_assessment': analysis_data.get('primary_assessment', 'Analysis completed'),
            'confidence': analysis.get('confidence_score', 0),
            'key_metrics': key_metrics if key_metrics else None,
            'has_red_flags': has_red_flags,
            'red_flag_count': red_flag_count,
            'trend': trend,
            'urgency_level': urgency_level,
            'analysis_data': analysis_data  # Full data for detailed viewing
        }
        
        analysis_entries.append(entry)
        
        # Track current index if specified
        if current_analysis_id and analysis['id'] == current_analysis_id:
            current_index = idx
    
    # Calculate date range
    date_range = {
        'start': analyses[0]['created_at'] if analyses else None,
        'end': analyses[-1]['created_at'] if analyses else None
    }
    
    # Build response
    return {
        'analyses': analysis_entries,
        'current_index': current_index,
        'session_info': {
            'condition_name': session.get('condition_name', 'Unknown condition'),
            'total_analyses': len(analyses),
            'date_range': date_range
        }
    }