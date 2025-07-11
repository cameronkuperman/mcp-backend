"""
Run just the API server for testing
"""
import uvicorn
from api_routes import api

if __name__ == "__main__":
    print("Starting API Server (no MCP)...")
    print("Server running at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Health check at: http://localhost:8000/health")
    print("\nPress CTRL+C to stop the server")
    
    uvicorn.run(api, host="0.0.0.0", port=8000)