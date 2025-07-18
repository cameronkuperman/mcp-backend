"""Core middleware configurations"""
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Setup CORS middleware"""
    # ALLOW EVERYTHING - NO RESTRICTIONS
    print("CORS: Allowing ALL origins with credentials")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow ALL origins
        allow_credentials=False,  # Must be False when allowing all origins
        allow_methods=["*"],  # Allow ALL methods
        allow_headers=["*"],  # Allow ALL headers
        expose_headers=["*"],  # Expose ALL headers
        max_age=3600
    )