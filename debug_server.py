#!/usr/bin/env python3
"""Debug server with comprehensive logging"""
import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Create a simple test app
app = FastAPI()

@app.get("/")
async def root():
    logger.info("Root endpoint hit")
    return {"message": "Server is running"}

@app.get("/health")
async def health():
    logger.info("Health endpoint hit")
    return {"status": "healthy", "service": "Debug Server"}

@app.post("/test-chat")
async def test_chat(request: Request):
    logger.info("Test chat endpoint hit")
    try:
        body = await request.json()
        logger.debug(f"Request body: {body}")
        
        # Test basic response without calling LLM
        return {
            "response": "This is a test response without LLM",
            "request_received": body,
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error in test-chat: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )

if __name__ == "__main__":
    print("Starting Debug Server...")
    print("URL: http://localhost:8000")
    print("Endpoints:")
    print("  GET  /         - Root")
    print("  GET  /health   - Health check")
    print("  POST /test-chat - Test chat (no LLM)")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")