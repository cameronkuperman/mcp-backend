"""Photo analysis endpoints with intelligent question detection"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import base64
import time
import traceback
from typing import List, Dict

from models.requests import PhotoAnalysisRequest, PhotoAnalysisResponse
from utils.json_parser import extract_json_from_text
from ..core import PHOTO_ANALYSIS_PROMPT, PHOTO_COMPARISON_PROMPT, STORAGE_BUCKET
from ..openrouter import call_openrouter, call_openrouter_with_retry
from ..database import get_supabase

router = APIRouter()
supabase = get_supabase()

@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photos(request: PhotoAnalysisRequest):
    """Analyze photos using GPT-5 with automatic question detection"""
    print(f"Analyze request received - session_id: {request.session_id}, photo_ids: {request.photo_ids}")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not configured")
    
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
                base64_image = photo['temporary_data']
            else:
                print(f"No storage URL or temporary data for photo {photo['id']}")
                raise HTTPException(status_code=400, detail="Cannot analyze photo without data")
        
        # Get proper mime type from file metadata or default to jpeg
        mime_type = photo.get('file_metadata', {}).get('mime_type', 'image/jpeg')
        photo_contents.append({
            'type': 'image_url',
            'image_url': {'url': f'data:{mime_type};base64,{base64_image}'}
        })
    
    # Build analysis prompt - USES ENHANCED PROMPT WITH QUESTION DETECTION
    analysis_prompt = PHOTO_ANALYSIS_PROMPT
    if request.context:
        # Include user's description/context for question detection
        analysis_prompt += f"\n\nUser's description/question: {request.context}"
    
    # Call AI for analysis with retry
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
                max_tokens=6000,
                temperature=0.1,
                max_retries=2
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
        print(f"AI response content: {content[:500]}...")
        analysis = extract_json_from_text(content)
        print(f"Extracted analysis: {analysis}")
        
        # Check if JSON extraction failed
        if analysis is None:
            raise ValueError(f"Failed to parse JSON from AI response. Content: {content[:1000]}")
        
        # Log if question was detected
        if analysis.get('question_detected'):
            print(f"Question detected! Answer: {analysis.get('question_answer', 'No answer provided')[:200]}...")
        
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
                max_tokens=4000,
                temperature=0.1,
                max_retries=2
            )
            
            content = response['choices'][0]['message']['content']
            analysis = extract_json_from_text(content)
            
            if analysis is None:
                raise ValueError(f"Failed to parse JSON from fallback AI response. Content: {content[:1000]}")
            
            # Log if question was detected in fallback
            if analysis.get('question_detected'):
                print(f"Question detected in fallback! Answer: {analysis.get('question_answer', 'No answer')[:200]}...")
            
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
            
        except Exception as e2:
            print(f"Fallback model also failed: {str(e2)}")
            print(f"Error type: {type(e2).__name__}")
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
                        continue
            
            # Call AI for comparison
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
                        max_tokens=3000,
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
        'model_used': 'openai/gpt-5',
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
    
    # Build response - includes optional question_answer field
    response_data = {
        'analysis_id': analysis_id,
        'analysis': analysis,  # This includes question_detected and question_answer if present
        'comparison': comparison,
        'expires_at': analysis_record.data[0].get('expires_at')
    }
    
    return response_data