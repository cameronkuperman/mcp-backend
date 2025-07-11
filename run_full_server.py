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
    print("Starting Full MCP + HTTP Server...")
    print("Server running at: http://localhost:8000")
    print("API docs at: http://localhost:8000/api/docs")
    print("MCP endpoints at: http://localhost:8000/")
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
    uvicorn.run(app, host="0.0.0.0", port=8000)