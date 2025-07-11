#!/usr/bin/env python3
"""
All the ways to get ASGI apps from FastMCP for use with uvicorn
"""

from fastmcp import FastMCP

# Create your FastMCP server
mcp = FastMCP("my-server")

# Add some tools, resources, prompts...
@mcp.tool()
async def example_tool(text: str) -> str:
    """An example tool"""
    return f"Processed: {text}"

# === Different ASGI Apps Available ===

# 1. Standard HTTP Transport (JSON-RPC over HTTP)
# This is the most common option for MCP servers
http_app = mcp.http_app()
# Run with: uvicorn fastmcp_asgi_apps:http_app

# 2. HTTP with custom path
http_app_custom = mcp.http_app(path="/mcp")
# The MCP endpoint will be at http://localhost:8000/mcp

# 3. HTTP with stateless mode (no session management)
stateless_app = mcp.http_app(stateless_http=True)

# 4. Server-Sent Events Transport
sse_app = mcp.sse_app()
# Run with: uvicorn fastmcp_asgi_apps:sse_app

# 5. SSE with custom paths
sse_custom = mcp.sse_app(
    path="/events",           # SSE endpoint
    message_path="/messages"  # Message posting endpoint
)

# 6. Streamable HTTP Transport
streamable_app = mcp.streamable_http_app()
# Run with: uvicorn fastmcp_asgi_apps:streamable_app

# === Advanced Options ===

# Add middleware to any app
from starlette.middleware.cors import CORSMiddleware

app_with_cors = mcp.http_app(
    middleware=[
        (CORSMiddleware, {
            "allow_origins": ["*"],
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        })
    ]
)

# You can also customize the transport type in http_app
app_sse_via_http = mcp.http_app(transport="sse")
app_streamable_via_http = mcp.http_app(transport="streamable-http")

# === Running with uvicorn ===
# From command line:
# uvicorn fastmcp_asgi_apps:http_app --reload
# uvicorn fastmcp_asgi_apps:sse_app --reload --port 8001
# uvicorn fastmcp_asgi_apps:streamable_app --reload --port 8002

# Or programmatically:
if __name__ == "__main__":
    import uvicorn
    
    # Choose which app to run
    selected_app = http_app  # or sse_app, streamable_app, etc.
    
    uvicorn.run(
        selected_app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )