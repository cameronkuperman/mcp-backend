"""Helper functions for photo analysis"""
import re
import base64
import asyncio
from typing import Dict, Any, List
from fastapi import HTTPException, UploadFile
from .core import MAX_FILE_SIZE, ALLOWED_MIME_TYPES

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
    
    return {
        'filename': file.filename,
        'content_type': file.content_type,
        'size': file.size
    }