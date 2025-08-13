"""
Database Storage Helper
Stores the new enhanced fields in Supabase after generation
"""

import logging
from typing import Dict, Any, Optional
from supabase_client import supabase

logger = logging.getLogger(__name__)


def store_enhanced_fields_for_general_assessment(
    assessment_id: str,
    enhanced_data: Dict[str, Any]
) -> bool:
    """
    Store the new enhanced fields for a general assessment.
    
    Args:
        assessment_id: The ID of the assessment to update
        enhanced_data: Dictionary containing the new fields
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract the fields to store
        update_data = {
            "severity_level": enhanced_data.get("severity_level"),
            "confidence_level": enhanced_data.get("confidence_level"),
            "what_this_means": enhanced_data.get("what_this_means"),
            "immediate_actions": enhanced_data.get("immediate_actions", []),
            "red_flags": enhanced_data.get("red_flags", []),
            "tracking_metrics": enhanced_data.get("tracking_metrics", []),
            "follow_up_timeline": enhanced_data.get("follow_up_timeline", {})
        }
        
        # Update the database
        result = supabase.table("general_assessments").update(update_data).eq("id", assessment_id).execute()
        
        logger.info(f"Stored enhanced fields for general assessment {assessment_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store enhanced fields for general assessment {assessment_id}: {e}")
        return False


def store_enhanced_fields_for_general_deepdive(
    session_id: str,
    enhanced_data: Dict[str, Any]
) -> bool:
    """
    Store the new enhanced fields for a general deep dive session.
    
    Args:
        session_id: The ID of the deep dive session to update
        enhanced_data: Dictionary containing the new fields
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract the fields to store
        update_data = {
            "severity_level": enhanced_data.get("severity_level"),
            "confidence_level": enhanced_data.get("confidence_level"),
            "what_this_means": enhanced_data.get("what_this_means"),
            "immediate_actions": enhanced_data.get("immediate_actions", []),
            "red_flags": enhanced_data.get("red_flags", []),
            "tracking_metrics": enhanced_data.get("tracking_metrics", []),
            "follow_up_timeline": enhanced_data.get("follow_up_timeline", {})
        }
        
        # Update the database
        result = supabase.table("general_deepdive_sessions").update(update_data).eq("id", session_id).execute()
        
        logger.info(f"Stored enhanced fields for general deep dive {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store enhanced fields for general deep dive {session_id}: {e}")
        return False


def store_minimal_fields_for_quick_scan(
    scan_id: str,
    what_this_means: Optional[str],
    immediate_actions: Optional[list]
) -> bool:
    """
    Store the minimal enhanced fields for a quick scan.
    
    Args:
        scan_id: The ID of the quick scan to update
        what_this_means: Plain English explanation
        immediate_actions: List of immediate actions
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Only update if we have values
        update_data = {}
        if what_this_means:
            update_data["what_this_means"] = what_this_means
        if immediate_actions:
            update_data["immediate_actions"] = immediate_actions
            
        if update_data:
            result = supabase.table("quick_scans").update(update_data).eq("id", scan_id).execute()
            logger.info(f"Stored minimal fields for quick scan {scan_id}")
            return True
        
        return True  # Nothing to update
        
    except Exception as e:
        logger.error(f"Failed to store minimal fields for quick scan {scan_id}: {e}")
        return False


def store_minimal_fields_for_deep_dive(
    session_id: str,
    what_this_means: Optional[str],
    immediate_actions: Optional[list]
) -> bool:
    """
    Store the minimal enhanced fields for a deep dive session.
    
    Args:
        session_id: The ID of the deep dive session to update
        what_this_means: Plain English explanation
        immediate_actions: List of immediate actions
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Only update if we have values
        update_data = {}
        if what_this_means:
            update_data["what_this_means"] = what_this_means
        if immediate_actions:
            update_data["immediate_actions"] = immediate_actions
            
        if update_data:
            result = supabase.table("deep_dive_sessions").update(update_data).eq("id", session_id).execute()
            logger.info(f"Stored minimal fields for deep dive {session_id}")
            return True
        
        return True  # Nothing to update
        
    except Exception as e:
        logger.error(f"Failed to store minimal fields for deep dive {session_id}: {e}")
        return False