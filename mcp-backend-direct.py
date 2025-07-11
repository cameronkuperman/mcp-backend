from mcp_server import mcp
from api_routes import api

# Instead of mounting, add routes directly to the MCP server
# This requires FastMCP to have an internal app attribute
if hasattr(mcp, '_app') or hasattr(mcp, 'app'):
    app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None)
    if app:
        # Mount FastAPI routes on the internal Starlette/FastAPI app
        app.mount("/api", api)
    else:
        # Fallback: try to add individual routes
        for route in api.routes:
            if hasattr(route, 'path') and hasattr(route, 'endpoint'):
                # Adjust paths to include /api prefix
                route.path = f"/api{route.path}"
                mcp.add_route(route)
else:
    print("Warning: Could not find internal app to mount routes")


if __name__ == "__main__":
    mcp.run()