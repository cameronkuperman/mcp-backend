#!/usr/bin/env python3
"""Oracle Server - Main entry point"""
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

# Import routers
from api.chat import router as chat_router
from api.health_scan import router as health_scan_router
from api.health_story import router as health_story_router
from api.tracking import router as tracking_router
from api.photo_analysis import router as photo_analysis_router

from api.population_health import router as population_health_router
from api.reports.general import router as general_reports_router
from api.reports.specialist import router as specialist_reports_router
from api.reports.time_based import router as time_based_reports_router
from api.reports.urgent import router as urgent_reports_router

# Import middleware
from core.middleware import setup_cors

load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Oracle Health API",
    description="AI-powered health analysis and tracking",
    version="2.0.0"
)

# Setup middleware
setup_cors(app)

# Include routers
app.include_router(chat_router)
app.include_router(health_scan_router)
app.include_router(health_story_router)
app.include_router(tracking_router)
app.include_router(photo_analysis_router)
app.include_router(population_health_router)
app.include_router(general_reports_router)
app.include_router(specialist_reports_router)
app.include_router(time_based_reports_router)
app.include_router(urgent_reports_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Oracle Health API v2.0",
        "status": "healthy",
        "docs": "/docs"
    }

# Run the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "run_oracle:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development"
    )