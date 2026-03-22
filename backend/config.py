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


config = Config()
