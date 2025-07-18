"""Core middleware configurations"""
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Setup CORS middleware"""
    # Get allowed origins from environment or default to all
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # If "*" is in the list, allow all origins
    if "*" in allowed_origins:
        allowed_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600
    )