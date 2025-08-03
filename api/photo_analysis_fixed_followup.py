"""Fixed follow-up endpoint with comprehensive error handling"""
from fastapi import HTTPException, UploadFile, File, Form
from typing import List, Optional, Dict, Any
import json
import traceback
import httpx
from datetime import datetime
import os

# This is the fixed version of add_follow_up_photos with proper error handling

@router.post("/session/{session_id}/follow-up")
async def add_follow_up_photos(
    session_id: str,
    photos: List[UploadFile] = File(...),
    auto_compare: bool = Form(True),
    notes: Optional[str] = Form(None),
    compare_with_photo_ids: Optional[str] = Form(None)  # JSON string of photo IDs
):
    """Add follow-up photos to an existing session and optionally compare with previous photos"""
    start_time = datetime.utcnow()
    
    try:
        # Enhanced logging
        print(f"\n{'='*60}")
        print(f"Follow-up endpoint called at {start_time.isoformat()}")
        print(f"Session ID: {session_id}")
        print(f"Number of photos: {len(photos) if photos else 0}")
        print(f"Auto compare: {auto_compare}")
        print(f"Notes: {notes}")
        print(f"Compare with IDs: {compare_with_photo_ids}")
        print(f"{'='*60}\n")
        
        # Validate configuration
        if not supabase:
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "configuration_error",
                    "message": "Database connection not configured"
                }
            )
        if not OPENROUTER_API_KEY:
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "configuration_error",
                    "message": "OpenRouter API key not configured"
                }
            )
        
        # Validate input
        if len(photos) > 5:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "validation_error",
                    "message": "Maximum 5 photos per follow-up upload"
                }
            )
        
        # Verify session exists
        try:
            session_result = supabase.table('photo_sessions').select('*').eq('id', session_id).single().execute()
            if not session_result.data:
                raise HTTPException(
                    status_code=404, 
                    detail={
                        "error": "not_found",
                        "message": "Session not found"
                    }
                )
        except Exception as e:
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=404, 
                    detail={
                        "error": "not_found",
                        "message": "Session not found"
                    }
                )
            raise
        
        session = session_result.data
        user_id = session['user_id']
        
        # Parse compare_with_photo_ids if provided
        comparison_photo_ids = []
        if compare_with_photo_ids:
            try:
                comparison_photo_ids = json.loads(compare_with_photo_ids)
            except json.JSONDecodeError as e:
                print(f"Failed to parse compare_with_photo_ids: {e}")
                comparison_photo_ids = []
        
        # Initialize variables
        smart_batching_info = None
        comparison_photos = []
        
        # Get previous photos for comparison
        if auto_compare and not comparison_photo_ids:
            try:
                # Get ALL photos from this session for smart selection
                all_prev_photos_result = supabase.table('photo_uploads')\
                    .select('*')\
                    .eq('session_id', session_id)\
                    .eq('category', 'medical_normal')\
                    .order('uploaded_at')\
                    .execute()
                
                if all_prev_photos_result.data:
                    print(f"Found {len(all_prev_photos_result.data)} previous photos for smart batching")
                    
                    # Use smart batching if more than 40 photos
                    if len(all_prev_photos_result.data) > 40:
                        smart_batcher = SmartPhotoBatcher()
                        batch_result = smart_batcher.select_photos_for_comparison(
                            all_prev_photos_result.data,
                            max_photos=40
                        )
                        comparison_photos = batch_result['selected_photos']
                        smart_batching_info = batch_result['batch_info']
                        print(f"Smart batching selected {len(comparison_photos)} photos")
                    else:
                        # Use last 3 photos for comparison
                        comparison_photos = all_prev_photos_result.data[-3:]
            except Exception as e:
                print(f"Error fetching previous photos: {e}")
                # Continue without comparison
        
        elif comparison_photo_ids:
            # Get specific photos by IDs
            try:
                specific_photos_result = supabase.table('photo_uploads')\
                    .select('*')\
                    .in_('id', comparison_photo_ids)\
                    .execute()
                comparison_photos = specific_photos_result.data if specific_photos_result.data else []
            except Exception as e:
                print(f"Error fetching specific photos: {e}")
        
        # Process uploaded photos
        uploaded_photos = []
        
        for photo in photos:
            try:
                # Validate photo
                await validate_photo_upload(photo)
                
                # Categorize using Gemini Flash Lite
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
                    
                    if not categorization:
                        raise ValueError("Failed to extract JSON from categorization response")
                    
                    category = categorization.get('category', 'unclear')
                    
                except Exception as e:
                    print(f"Categorization error: {e}")
                    category = 'unclear'
                    categorization = {'category': 'unclear', 'confidence': 0}
                
                # Handle based on category
                photo_id = str(uuid.uuid4())
                storage_url = None
                
                if category in ['medical_normal', 'medical_gore']:
                    # Upload to storage
                    try:
                        sanitized_filename = sanitize_filename(photo.filename)
                        file_name = f"{user_id}/{session_id}/{datetime.now().timestamp()}_{sanitized_filename}"
                        
                        await photo.seek(0)
                        file_data = await photo.read()
                        
                        upload_response = supabase.storage.from_(STORAGE_BUCKET).upload(
                            file_name,
                            file_data,
                            file_options={"content-type": photo.content_type}
                        )
                        
                        storage_url = file_name
                        
                    except Exception as e:
                        print(f"Storage upload error: {e}")
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "storage_error",
                                "message": "Failed to upload photo to storage"
                            }
                        )
                
                # Save to database
                try:
                    db_entry = {
                        'id': photo_id,
                        'user_id': user_id,
                        'session_id': session_id,
                        'storage_url': storage_url,
                        'category': category,
                        'categorization_confidence': categorization.get('confidence', 0),
                        'metadata': {
                            'filename': photo.filename,
                            'size': photo.size,
                            'mime_type': photo.content_type,
                            'notes': notes,
                            'quality_score': categorization.get('quality_score')
                        }
                    }
                    
                    insert_result = supabase.table('photo_uploads').insert(db_entry).execute()
                    
                    if insert_result.data:
                        uploaded_photos.append(insert_result.data[0])
                    
                except Exception as e:
                    print(f"Database insert error: {e}")
                    raise
                    
            except Exception as e:
                print(f"Error processing photo {photo.filename}: {e}")
                # Continue with other photos
                continue
        
        if not uploaded_photos:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_valid_photos",
                    "message": "No valid photos could be processed"
                }
            )
        
        # Perform analysis on the first photo
        analysis_response = None
        try:
            if uploaded_photos and uploaded_photos[0]['storage_url']:
                # Generate signed URL
                url_data = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
                    uploaded_photos[0]['storage_url'],
                    3600
                )
                signed_url = url_data.get('signedURL') or url_data.get('signedUrl')
                
                # Fetch and convert to base64
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(signed_url)
                    img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                
                # Analyze using Gemini Pro
                try:
                    analysis_result = await call_openrouter_with_retry(
                        model='google/gemini-2.5-pro',
                        messages=[{
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': PHOTO_ANALYSIS_PROMPT},
                                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_base64}'}}
                            ]
                        }],
                        max_tokens=2000,
                        temperature=0.3
                    )
                    
                    analysis_content = analysis_result['choices'][0]['message']['content']
                    analysis_response = extract_json_from_text(analysis_content)
                    
                    if not analysis_response:
                        raise ValueError("Failed to extract JSON from analysis response")
                    
                    # Validate response structure
                    if 'analysis' in analysis_response:
                        analysis_data = analysis_response['analysis']
                    else:
                        analysis_data = analysis_response
                    
                    # Store analysis
                    analysis_entry = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'photo_ids': [p['id'] for p in uploaded_photos],
                        'analysis_type': 'follow_up',
                        'analysis_data': analysis_data,
                        'confidence_score': analysis_data.get('confidence', 50),
                        'ai_model': 'google/gemini-2.5-pro',
                        'metadata': {
                            'is_follow_up': True,
                            'comparison_count': len(comparison_photos)
                        }
                    }
                    
                    supabase.table('photo_analyses').insert(analysis_entry).execute()
                    
                except Exception as e:
                    print(f"Analysis error: {e}")
                    analysis_response = {
                        'primary_assessment': 'Analysis pending',
                        'confidence': 0,
                        'error': str(e)
                    }
                    
        except Exception as e:
            print(f"Analysis setup error: {e}")
            analysis_response = None
        
        # Perform comparison if we have photos to compare with
        comparison_results = {}
        if comparison_photos and analysis_response:
            try:
                # Compare with selected photos
                comparison_prompt = create_follow_up_comparison_prompt(
                    session.get('condition_name'),
                    comparison_photos,
                    uploaded_photos[0],
                    analysis_response
                )
                
                comp_result = await call_openrouter_with_retry(
                    model='google/gemini-2.5-pro',
                    messages=[{"role": "user", "content": comparison_prompt}],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                comp_content = comp_result['choices'][0]['message']['content']
                comp_response = extract_json_from_text(comp_content)
                
                if comp_response:
                    # Handle both nested and flat response structures
                    if 'comparison' in comp_response:
                        comparison_data = comp_response['comparison']
                    else:
                        comparison_data = comp_response
                    
                    comparison_results = {
                        'compared_with': [p['id'] for p in comparison_photos[-3:]],
                        'days_since_last': comparison_data.get('days_between', 0),
                        'analysis': {
                            'trend': comparison_data.get('progression_analysis', {}).get('overall_trend', 'unknown'),
                            'changes': comparison_data.get('visual_changes', {}),
                            'confidence': comparison_data.get('progression_analysis', {}).get('confidence_in_trend', 50),
                            'summary': comparison_data.get('clinical_interpretation', 'Comparison analysis completed')
                        },
                        'visual_comparison': comparison_data,
                        'key_measurements': {
                            'latest': analysis_response.get('key_measurements', {}),
                            'condition_insights': analysis_response.get('condition_insights', {})
                        }
                    }
                    
                    # Store comparison
                    comparison_entry = {
                        'user_id': user_id,
                        'session_id': session_id,
                        'photo_id': uploaded_photos[0]['id'],
                        'compared_photo_ids': [p['id'] for p in comparison_photos],
                        'comparison_data': comparison_data,
                        'trend': comparison_data.get('progression_analysis', {}).get('overall_trend'),
                        'measurement_deltas': comparison_data.get('visual_changes'),
                        'clinical_significance': comparison_data.get('clinical_interpretation'),
                        'primary_change': comparison_data.get('primary_change'),
                        'change_significance': comparison_data.get('change_significance')
                    }
                    
                    supabase.table('photo_comparisons').insert(comparison_entry).execute()
                    
            except Exception as e:
                print(f"Comparison error: {e}")
                traceback.print_exc()
                comparison_results = {
                    'error': 'Comparison failed',
                    'message': str(e)
                }
        
        # Generate follow-up suggestions
        follow_up_suggestion = {}
        try:
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
                analysis_response
            )
        except Exception as e:
            print(f"Follow-up suggestion error: {e}")
            follow_up_suggestion = {
                'benefits_from_tracking': True,
                'suggested_interval_days': 7,
                'reasoning': 'Continue monitoring as scheduled',
                'priority': 'routine'
            }
        
        # Prepare response
        result = {
            'uploaded_photos': uploaded_photos,
            'comparison_results': comparison_results,
            'follow_up_suggestion': follow_up_suggestion,
            'smart_batching_info': smart_batching_info
        }
        
        # Log success
        duration = (datetime.utcnow() - start_time).total_seconds()
        print(f"\nFollow-up endpoint completed successfully in {duration:.2f}s")
        print(f"Uploaded: {len(uploaded_photos)} photos")
        print(f"Compared with: {len(comparison_photos)} photos")
        print(f"{'='*60}\n")
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as they have proper error structure
        raise
        
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP Status Error in follow-up endpoint:")
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text[:500]}")
        traceback.print_exc()
        
        if e.response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "rate_limit",
                    "message": "AI service is temporarily busy. Please try again in 30 seconds.",
                    "retry_after": 30
                }
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ai_service_error",
                    "message": f"AI service error: {e.response.status_code}"
                }
            )
            
    except json.JSONDecodeError as e:
        print(f"\nJSON Decode Error in follow-up endpoint:")
        print(f"Error: {e}")
        print(f"Content preview: {str(e.doc)[:500] if hasattr(e, 'doc') else 'N/A'}")
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "json_parse_error",
                "message": "Failed to parse AI response. Please try again."
            }
        )
        
    except Exception as e:
        print(f"\nUnexpected error in follow-up endpoint:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        print(f"Failed after {duration:.2f}s")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
                "debug": str(e) if os.getenv("DEBUG") else None
            }
        )