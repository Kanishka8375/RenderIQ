"""Application configuration."""

import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    # Production settings
    ENV = os.environ.get("RENDERIQ_ENV", "development")
    DEBUG = ENV != "production"
    ADMIN_API_KEY = os.environ.get("RENDERIQ_ADMIN_KEY", "renderiq-dev-key")
    ALLOWED_ORIGINS = (
        ["*"] if ENV != "production"
        else [
            "https://renderiq.in",
            "https://www.renderiq.in",
        ]
    )
    RATE_LIMIT_UPLOADS = "5/hour" if ENV == "production" else "1000/hour"
    FEEDBACK_FILE = os.path.join(ROOT_DIR, "feedback.json")
    ANALYTICS_FILE = os.path.join(ROOT_DIR, "analytics.json")


config = Config()
