"""Core middleware configurations"""
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Setup CORS middleware - Allow all origins"""
    print("CORS: Allowing ALL origins")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow ALL origins
        allow_credentials=True,  # Allow credentials
        allow_methods=["*"],  # Allow ALL methods
        allow_headers=["*"],  # Allow ALL headers
        expose_headers=["*"],  # Expose ALL headers
        max_age=3600
    )