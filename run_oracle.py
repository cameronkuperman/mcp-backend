#!/usr/bin/env python3
"""Oracle Server - Main entry point"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv
import logging

# Import routers
from api.chat import router as chat_router
from api.health_scan import router as health_scan_router
from api.health_story import router as health_story_router
from api.tracking import router as tracking_router
from api.photo_analysis import router as photo_analysis_router
from api.health_analysis import router as health_analysis_router
from api.export import router as export_router

from api.population_health import router as population_health_router
from api.reports.general import router as general_reports_router
from api.reports.specialist import router as specialist_reports_router
from api.reports.specialist_extended import router as specialist_extended_router
from api.reports.time_based import router as time_based_reports_router
from api.reports.urgent import router as urgent_reports_router
from api.ai_predictions import router as ai_predictions_router
from api.health_score import router as health_score_router
from api.general_assessment import router as general_assessment_router
from api.follow_up import router as follow_up_router

# Import intelligence routers
from api.intelligence.weekly_brief import router as weekly_brief_router
from api.intelligence.health_velocity import router as health_velocity_router
from api.intelligence.body_systems import router as body_systems_router
from api.intelligence.timeline import router as timeline_router
from api.intelligence.patterns import router as patterns_router
from api.intelligence.doctor_readiness import router as doctor_readiness_router
from api.intelligence.comparative import router as comparative_router

# Import middleware
from core.middleware import setup_cors

# Import background jobs - using enhanced v2 with FAANG-level optimizations
from services.background_jobs_v2 import init_scheduler, shutdown_scheduler
# Import async HTTP client cleanup
from utils.async_http import close_http_client

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Oracle Health API with background scheduler...")
    await init_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down Oracle Health API...")
    await shutdown_scheduler()
    # Clean up HTTP client connections
    await close_http_client()
    logger.info("Closed HTTP client connections")

# Create FastAPI app
app = FastAPI(
    title="Oracle Health API",
    description="AI-powered health analysis and tracking with intelligence features",
    version="3.0.0",
    lifespan=lifespan
)

# Setup middleware
setup_cors(app)

# Include routers
app.include_router(chat_router)
app.include_router(health_scan_router)
app.include_router(health_story_router)
app.include_router(tracking_router)
app.include_router(photo_analysis_router)
app.include_router(health_analysis_router)
app.include_router(export_router)
app.include_router(population_health_router)
app.include_router(general_reports_router)
app.include_router(specialist_reports_router)
app.include_router(specialist_extended_router)
app.include_router(time_based_reports_router)
app.include_router(urgent_reports_router)
app.include_router(ai_predictions_router)
app.include_router(health_score_router)
app.include_router(general_assessment_router)
app.include_router(follow_up_router)

# Include intelligence routers
app.include_router(weekly_brief_router)
app.include_router(health_velocity_router)
app.include_router(body_systems_router)
app.include_router(timeline_router)
app.include_router(patterns_router)
app.include_router(doctor_readiness_router)
app.include_router(comparative_router)

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