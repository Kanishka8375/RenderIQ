"""File storage management for uploads and job outputs."""

import os
import shutil

from backend.config import config


def ensure_dirs():
    """Create required directories if they don't exist."""
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.JOBS_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.PRESETS_DIR, exist_ok=True)


def get_job_upload_dir(job_id: str) -> str:
    """Get or create upload directory for a job."""
    path = os.path.join(config.UPLOAD_DIR, job_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_job_work_dir(job_id: str) -> str:
    """Get or create working directory for a job."""
    path = os.path.join(config.JOBS_DIR, job_id)
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_job(job_id: str):
    """Delete all files for a job."""
    upload_dir = os.path.join(config.UPLOAD_DIR, job_id)
    work_dir = os.path.join(config.JOBS_DIR, job_id)
    for d in [upload_dir, work_dir]:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)


def get_free_disk_space_mb() -> float:
    """Return free disk space in MB."""
    path = config.UPLOAD_DIR
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
    stat = os.statvfs(path)
    return (stat.f_bavail * stat.f_frsize) / (1024 * 1024)


def validate_upload_size(file_size: int) -> str | None:
    """Return error message if file is too large, else None."""
    if file_size > config.MAX_UPLOAD_SIZE_BYTES:
        return f"File too large. Maximum size is {config.MAX_UPLOAD_SIZE_MB}MB."
    return None


def validate_disk_space() -> str | None:
    """Return error message if disk space is too low, else None."""
    free_mb = get_free_disk_space_mb()
    if free_mb < 1024:
        return f"Low disk space ({free_mb:.0f}MB free). Need at least 1GB."
    return None
