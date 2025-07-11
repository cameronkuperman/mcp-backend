from mcp_server import mcp
from api_routes import api
from fastmcp import FastMCP

# Create a FastMCP wrapper for the FastAPI app
api_mcp = FastMCP.from_fastapi(api, name="Medical API")

# Mount the wrapped API on the MCP server
mcp.mount(api_mcp, prefix="/api")


if __name__ == "__main__":
    mcp.run()