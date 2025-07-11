#!/usr/bin/env python3
"""
Working server that combines MCP and HTTP properly
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api_routes import api
from mcp_server import mcp
from fastmcp import FastMCP

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Create main FastAPI app
main_app = FastAPI(title="Oracle Medical Backend")

# Add CORS
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the API routes directly on main app
main_app.mount("/api", api)

# Add a root endpoint
@main_app.get("/")
async def root():
    return {
        "message": "Oracle Medical Backend",
        "endpoints": {
            "api_docs": "http://localhost:8000/api/docs",
            "api_health": "http://localhost:8000/api/health",
            "api_chat": "POST http://localhost:8000/api/chat"
        }
    }

if __name__ == "__main__":
    print("\n🚀 Starting Oracle Medical Backend Server")
    print("=" * 50)
    print("📍 Server URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/api/docs")
    print("❤️  Health Check: http://localhost:8000/api/health")
    print("💬 Chat Endpoint: POST http://localhost:8000/api/chat")
    print("=" * 50)
    print("Press CTRL+C to stop\n")
    
    try:
        uvicorn.run(main_app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n👋 Server stopped")