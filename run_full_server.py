"""
Run the full MCP + HTTP server on a single port
"""
from mcp_server import mcp
from api_routes import api
from fastmcp import FastMCP
import uvicorn

# Create a FastMCP wrapper for the FastAPI app
api_mcp = FastMCP.from_fastapi(api, name="Medical API")

# Mount the wrapped API on the MCP server
mcp.mount(api_mcp, prefix="/api")

if __name__ == "__main__":
    import os
    
    # Get port from environment (Railway provides this)
    port = int(os.environ.get("PORT", 8000))
    
    print("Starting Full MCP + HTTP Server...")
    print(f"Server running at: http://localhost:{port}")
    print(f"API docs at: http://localhost:{port}/api/docs")
    print(f"MCP endpoints at: http://localhost:{port}/")
    print("\nAvailable MCP Tools:")
    print("- oracle_query")
    print("- health_scan_query") 
    print("- quick_scan_query")
    print("- deep_dive_query")
    print("- create_llm_summary")
    print("\nPress CTRL+C to stop the server")
    
    # Run with HTTP transport instead of STDIO
    # Get the ASGI app from FastMCP
    app = mcp.http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)