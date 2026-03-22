"""File upload endpoints."""

import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from backend.config import config
from backend.models.schemas import UploadResponse, ReferenceUploadResponse, ErrorResponse
from backend.services.job_manager import job_manager
from backend.services.storage import (
    get_job_upload_dir, validate_disk_space, validate_upload_size,
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from renderiq.utils import get_video_info, validate_video, SUPPORTED_FORMATS

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/raw", response_model=UploadResponse)
async def upload_raw(file: UploadFile = File(...)):
    """Upload raw footage video file."""
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(SUPPORTED_FORMATS)}",
        )

    # Check disk space
    disk_err = validate_disk_space()
    if disk_err:
        raise HTTPException(status_code=507, detail=disk_err)

    # Generate job ID and save file
    job_id = uuid.uuid4().hex[:12]
    upload_dir = get_job_upload_dir(job_id)
    file_path = os.path.join(upload_dir, f"raw{ext}")

    # Stream to disk with size check
    total_size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            total_size += len(chunk)
            size_err = validate_upload_size(total_size)
            if size_err:
                f.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail=size_err)
            f.write(chunk)

    # Validate video
    validation = validate_video(file_path)
    if validation is not True:
        error_msg = validation.get("error", "Invalid video file") if isinstance(validation, dict) else "Invalid video file"
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=error_msg)

    # Get video info
    info = get_video_info(file_path)

    # Check duration limit
    if info["duration"] > config.MAX_VIDEO_DURATION_MINUTES * 60:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Video too long ({info['duration']/60:.1f} min). Max is {config.MAX_VIDEO_DURATION_MINUTES} minutes.",
        )

    # Create job
    job = job_manager.create_job(job_id)
    job.raw_path = file_path
    job.raw_filename = file.filename or f"video{ext}"
    job.duration = info["duration"]
    job.width = info["width"]
    job.height = info["height"]
    job.fps = info["fps"]
    job.file_size = total_size

    return UploadResponse(
        job_id=job_id,
        filename=file.filename or f"video{ext}",
        duration=round(info["duration"], 1),
        resolution=f"{info['width']}x{info['height']}",
        fps=round(info["fps"], 1),
        file_size_mb=round(total_size / (1024 * 1024), 1),
    )


@router.post("/reference", response_model=ReferenceUploadResponse)
async def upload_reference(
    job_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload reference video for a job."""
    # Validate job exists
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(SUPPORTED_FORMATS)}",
        )

    # Save file
    upload_dir = get_job_upload_dir(job_id)
    file_path = os.path.join(upload_dir, f"reference{ext}")

    total_size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            size_err = validate_upload_size(total_size)
            if size_err:
                f.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail=size_err)
            f.write(chunk)

    # Validate video
    validation = validate_video(file_path)
    if validation is not True:
        error_msg = validation.get("error", "Invalid video file") if isinstance(validation, dict) else "Invalid video file"
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=error_msg)

    job_manager.update_job(job_id, reference_path=file_path)

    return ReferenceUploadResponse(job_id=job_id, reference_uploaded=True)


@router.post("/url")
async def upload_url():
    """Upload video from URL — coming soon."""
    raise HTTPException(
        status_code=501,
        detail="URL upload coming soon. Please upload a file directly.",
    )
