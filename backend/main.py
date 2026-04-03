"""FastAPI application for RenderIQ web interface."""

import asyncio
import logging
import os
import sys
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import config
from backend.services.storage import ensure_dirs
from backend.services.job_manager import job_manager
from backend.routes import upload, grade, presets, download, admin, ai_edit

logger = logging.getLogger("renderiq.api")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


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
    logger.info("RenderIQ API starting up (env=%s)", config.ENV)

    # Generate presets if they don't exist
    from renderiq.presets_builder import generate_all_presets, PRESETS_DIR
    if not os.path.isdir(PRESETS_DIR) or len(os.listdir(PRESETS_DIR)) < 10:
        logger.info("Generating built-in presets...")
        generate_all_presets(size=17)
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
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if config.DEBUG else None,
    redoc_url=None,
)

# Rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


# Global exception handler for production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if config.DEBUG:
        raise exc
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# Request logging + security headers middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "%s %s %s %.3fs %s",
        request.client.host if request.client else "-",
        request.method,
        request.url.path,
        duration,
        response.status_code,
    )
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not config.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'"
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(upload.router)
app.include_router(grade.router)
app.include_router(presets.router)
app.include_router(download.router)
app.include_router(admin.router)
app.include_router(ai_edit.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# Serve frontend static files if build exists
frontend_build = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(frontend_build):
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
