"""Core middleware configurations"""
from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Setup CORS middleware"""
    # Configure allowed origins
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://localhost:3000",
        "https://localhost:3001",
        "https://proxima-eight-pi.vercel.app",  # Production Vercel URL
        "https://proxima-1.health",  # Production domain
        "https://*.vercel.app",  # All Vercel preview deployments
        # Add your production frontend URL here
        # "https://your-frontend-domain.com"
    ]
    
    # For development, you might want to allow more origins
    if os.getenv("ENVIRONMENT", "development") == "development":
        allowed_origins.extend([
            "http://localhost:*",
            "http://127.0.0.1:*"
        ])
    
    print(f"CORS: Allowing origins with credentials: {allowed_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Specific origins for credentials
        allow_credentials=True,  # Allow credentials
        allow_methods=["*"],  # Allow ALL methods
        allow_headers=["*"],  # Allow ALL headers
        expose_headers=["*"],  # Expose ALL headers
        max_age=3600
    )