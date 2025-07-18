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
    
    # Strip whitespace from origins
    allowed_origins = [origin.strip() for origin in allowed_origins]
    
    # When allowing all origins, we can't use credentials
    allow_credentials = "*" not in allowed_origins
    
    # Add localhost variations for development
    if os.getenv("ENV") == "development" and "*" not in allowed_origins:
        localhost_origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003"
        ]
        for origin in localhost_origins:
            if origin not in allowed_origins:
                allowed_origins.append(origin)
    
    print(f"CORS: Allowed origins: {allowed_origins}")
    print(f"CORS: Allow credentials: {allow_credentials}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600
    )