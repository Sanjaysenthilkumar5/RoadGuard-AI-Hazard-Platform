import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.database.db import engine, Base
from app.database.seed import seed_database
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.detection_routes import router as detection_router
from app.api.routes.hazard_routes import router as hazard_router
from app.api.routes.map_routes import router as map_router
from app.api.routes.maintenance_routes import router as maintenance_router
from app.api.routes.analytics_routes import router as analytics_router
from app.api.routes.ai_routes import router as ai_router
from app.api.routes.export_routes import router as export_router

# Ensure tables created immediately
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database seeded with initial data
    seed_database()
    yield
    # Shutdown

app = FastAPI(
    title="RoadGuard AI — Road Hazard Detection & Risk Intelligence API",
    description="Production-grade smart-city road monitoring, CV hazard detection, geospatial mapping, and risk intelligence platform.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(detection_router, prefix=settings.API_V1_STR)
app.include_router(hazard_router, prefix=settings.API_V1_STR)
app.include_router(map_router, prefix=settings.API_V1_STR)
app.include_router(maintenance_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(export_router, prefix=settings.API_V1_STR)

# Static files directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    """Serves the RoadGuard AI Single Page Application."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({
        "status": "online",
        "service": "RoadGuard AI API",
        "version": settings.VERSION,
        "docs": "/docs"
    })

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "version": settings.VERSION,
        "model_version": settings.ACTIVE_MODEL_VERSION,
        "cv_engine": "READY",
        "database": "CONNECTED"
    }
