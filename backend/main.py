"""FastAPI application for RenderIQ web interface."""

import asyncio
import logging
import os
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import config
from backend.services.storage import ensure_dirs
from backend.services.job_manager import job_manager
from backend.routes import upload, grade, presets, download

logger = logging.getLogger("renderiq.api")


async def _periodic_cleanup():
    """Run job cleanup every CLEANUP_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(config.CLEANUP_INTERVAL_SECONDS)
        try:
            job_manager.cleanup_expired()
        except Exception as e:
            logger.warning("Cleanup error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("RenderIQ API starting up")

    # Generate presets if they don't exist
    from renderiq.presets_builder import generate_all_presets, PRESETS_DIR
    if not os.path.isdir(PRESETS_DIR) or len(os.listdir(PRESETS_DIR)) < 10:
        logger.info("Generating built-in presets...")
        generate_all_presets(size=17)  # Smaller size for faster generation
        logger.info("Built-in presets generated")

    # Start cleanup task
    cleanup_task = asyncio.create_task(_periodic_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("RenderIQ API shutting down")


app = FastAPI(
    title="RenderIQ API",
    description="AI Color Grade Transfer Tool",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(upload.router)
app.include_router(grade.router)
app.include_router(presets.router)
app.include_router(download.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


# Serve frontend static files if build exists
frontend_build = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(frontend_build):
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
