"""Application configuration."""

import os
import re
import secrets
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
    JOBS_DIR = os.path.join(ROOT_DIR, "jobs")
    OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
    PRESETS_DIR = os.path.join(ROOT_DIR, "presets", "builtin")
    ALLOWED_VIDEO_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    CLEANUP_INTERVAL_SECONDS = 300  # Check for expired jobs every 5 minutes

    # Job ID validation pattern (hex, 12 chars)
    JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

    # Production settings
    ENV = os.environ.get("RENDERIQ_ENV", "development")
    DEBUG = ENV != "production"
    ADMIN_API_KEY = os.environ.get("RENDERIQ_ADMIN_KEY") or (
        secrets.token_hex(16) if ENV != "production" else ""
    )
    ALLOWED_ORIGINS = (
        ["*"] if ENV != "production"
        else [
            "https://renderiq.in",
            "https://www.renderiq.in",
        ]
    )
    RATE_LIMIT_UPLOADS = _get_rate_limit()
    FEEDBACK_FILE = os.path.join(ROOT_DIR, "feedback.json")
    ANALYTICS_FILE = os.path.join(ROOT_DIR, "analytics.json")


config = Config()
