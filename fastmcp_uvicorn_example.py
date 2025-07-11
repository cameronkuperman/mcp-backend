#!/usr/bin/env python3
"""
Example showing how to use FastMCP with uvicorn directly
by accessing the ASGI app attributes
"""

from fastmcp import FastMCP

# Create a FastMCP instance
mcp = FastMCP("example-server")

# Add a simple tool for demonstration
@mcp.tool()
async def greet(name: str) -> str:
    """Greet someone by name"""
    return f"Hello, {name}!"

@mcp.tool()
async def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

# Get the ASGI app - there are three options:

# Option 1: Standard HTTP transport (default)
app = mcp.http_app()  # This returns a Starlette ASGI app

# Option 2: Server-Sent Events transport
# sse_app = mcp.sse_app()

# Option 3: Streamable HTTP transport  
# streamable_app = mcp.streamable_http_app()

# Now you can run this with uvicorn:
# uvicorn fastmcp_uvicorn_example:app --reload --port 8000

if __name__ == "__main__":
    # Alternative: use FastMCP's built-in runner which uses uvicorn internally
    import asyncio
    asyncio.run(mcp.run_http_async(port=8000))
    
    # Or just use the sync version
    # mcp.run(transport="http", port=8000)