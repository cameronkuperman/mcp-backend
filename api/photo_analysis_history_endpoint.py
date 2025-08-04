"""
Analysis History Endpoint for Frontend Photo Navigation

This module adds the new endpoint requested by the frontend team for 
viewing complete analysis history with photo navigation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException

async def get_analysis_history(
    session_id: str,
    current_analysis_id: Optional[str] = None,
    supabase=None,
    STORAGE_BUCKET=None
) -> Dict[str, Any]:
    """
    Get complete analysis history for a session with photo URLs
    
    Args:
        session_id: The photo session ID
        current_analysis_id: Optional current analysis to highlight
        supabase: Supabase client
        STORAGE_BUCKET: Storage bucket name
        
    Returns:
        Complete analysis history with navigation metadata
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
                    # In future, we could generate actual thumbnails
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
    response = {
        'analyses': analysis_entries,
        'current_index': current_index,
        'session_info': {
            'condition_name': session.get('condition_name', 'Unknown condition'),
            'total_analyses': len(analyses),
            'date_range': date_range
        }
    }
    
    return response


# Router endpoint to add to photo_analysis.py
"""
@router.get("/session/{session_id}/analysis-history")
async def get_analysis_history_endpoint(
    session_id: str,
    current_analysis_id: Optional[str] = Query(None)
):
    \"\"\"
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
    \"\"\"
    return await get_analysis_history(
        session_id=session_id,
        current_analysis_id=current_analysis_id,
        supabase=supabase,
        STORAGE_BUCKET=STORAGE_BUCKET
    )
"""