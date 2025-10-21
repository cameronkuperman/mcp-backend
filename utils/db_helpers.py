"""Minimal safe database helpers to prevent data[0] crashes"""
from typing import Optional, Dict, Any

def safe_get_first(result, context: str = "") -> Optional[Dict[str, Any]]:
    """
    Safely get first item from Supabase result.
    Returns None if data is empty/None instead of crashing.
    """
    try:
        if result and hasattr(result, 'data') and result.data and len(result.data) > 0:
            return result.data[0]
        print(f"⚠️  DB safe_get_first failed: {context}")
        return None
    except Exception as e:
        print(f"❌ DB safe_get_first exception: {str(e)} | {context}")
        return None
