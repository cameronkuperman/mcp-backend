from mcp_server import mcp
from api_routes import api

# Mount the HTTP API routes on the MCP server with as_proxy=True
# This tells FastMCP to wrap the FastAPI app appropriately
mcp.mount(api, prefix="/api", as_proxy=True)


if __name__ == "__main__":
    mcp.run()