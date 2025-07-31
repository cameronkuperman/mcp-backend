"""Core middleware configurations"""
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Setup CORS middleware - Allow specific origins for credentials"""
    
    # Define allowed origins for different environments
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://localhost:3000",
        "https://localhost:3001",
        "https://localhost:3002",
        "https://main--flourishing-taiyaki-fd4e09.netlify.app",
        "https://flourishing-taiyaki-fd4e09.netlify.app",
        "https://proxima-eight-pi.vercel.app",
        "https://*.vercel.app",
        "https://healthoracle.ai",
        "https://www.healthoracle.ai",
        "https://app.healthoracle.ai"
    ]
    
    # Add custom origins from environment variable if present
    custom_origins = os.getenv("CORS_ORIGINS", "").strip()
    if custom_origins:
        allowed_origins.extend(custom_origins.split(","))
    
    print(f"CORS: Allowing origins: {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Specific origins for credentials
        allow_credentials=True,  # Allow credentials
        allow_methods=["*"],  # Allow ALL methods
        allow_headers=["*"],  # Allow ALL headers
        expose_headers=["*"],  # Expose ALL headers
        max_age=3600
    )