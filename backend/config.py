"""Application configuration."""

import os
import re
import secrets
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = "/tmp/renderiq" if os.environ.get("VERCEL") else ROOT_DIR


def _is_testing() -> bool:
    """Check if running under pytest or TESTING env var."""
    return "pytest" in sys.modules or os.getenv("TESTING") == "1"


def _get_rate_limit() -> str:
    """Return appropriate rate limit for the current environment."""
    if _is_testing():
        return "1000/second"  # Effectively unlimited in tests
    if os.getenv("RENDERIQ_ENV") == "production":
        return "5/hour"
    return "100/hour"  # Development


class Config:
    MAX_UPLOAD_SIZE_MB = 500
    MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    MAX_VIDEO_DURATION_MINUTES = 10
    MAX_CONCURRENT_JOBS = 3
    JOB_EXPIRY_SECONDS = 3600  # 1 hour
    UPLOAD_DIR = os.path.join(_DATA_DIR, "uploads")
    JOBS_DIR = os.path.join(_DATA_DIR, "jobs")
    OUTPUT_DIR = os.path.join(_DATA_DIR, "output")
    PRESETS_DIR = os.path.join(ROOT_DIR, "presets", "builtin")
    ALLOWED_VIDEO_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    CLEANUP_INTERVAL_SECONDS = 300  # Check for expired jobs every 5 minutes

    # Job ID validation pattern (hex, 32 chars — 128-bit entropy)
    JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

    # Production settings
    ENV = os.environ.get("RENDERIQ_ENV", "development")
    if ENV not in ("development", "production", "testing"):
        raise ValueError(
            f"Invalid RENDERIQ_ENV='{ENV}'. Must be 'development', 'production', or 'testing'."
        )
    DEBUG = ENV != "production"
    ADMIN_API_KEY = os.environ.get("RENDERIQ_ADMIN_KEY") or (
        secrets.token_hex(16) if ENV != "production" else ""
    )
    ALLOWED_ORIGINS = ["*"]
    RATE_LIMIT_UPLOADS = _get_rate_limit()
    FEEDBACK_FILE = os.path.join(_DATA_DIR, "feedback.json")
    ANALYTICS_FILE = os.path.join(_DATA_DIR, "analytics.json")


config = Config()
