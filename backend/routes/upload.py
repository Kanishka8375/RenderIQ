"""File upload endpoints."""

import os
import secrets
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.auth import verify_job_token
from backend.config import config

limiter = Limiter(key_func=get_remote_address)
from backend.models.schemas import UploadResponse, ReferenceUploadResponse, ErrorResponse
from backend.services.job_manager import job_manager
from backend.services.storage import (
    get_job_upload_dir, validate_disk_space, validate_upload_size,
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from renderiq.utils import get_video_info, validate_video, SUPPORTED_FORMATS

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Known video container magic bytes / signatures
_VIDEO_SIGNATURES = [
    (b'\x00\x00\x00', 3, b'ftyp'),    # MP4/MOV (offset 4)
    (b'\x1a\x45\xdf\xa3', 0, None),    # MKV/WebM (EBML)
    (b'RIFF', 0, b'AVI '),              # AVI (RIFF....AVI )
    (b'\x00\x00\x01\xba', 0, None),    # MPEG-PS
    (b'\x00\x00\x01\xb3', 0, None),    # MPEG-1/2
    (b'\x47', 0, None),                 # MPEG-TS (sync byte)
]


def _check_video_magic(file_path: str) -> bool:
    """Fast check that file header looks like a video container."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)
    except OSError:
        return False

    if len(header) < 12:
        return False

    # MP4/MOV: bytes 4-7 should be 'ftyp'
    if header[4:8] == b'ftyp':
        return True

    # MKV/WebM: EBML header
    if header[:4] == b'\x1a\x45\xdf\xa3':
        return True

    # AVI: RIFF....AVI
    if header[:4] == b'RIFF' and header[8:12] == b'AVI ':
        return True

    # MPEG-PS / MPEG-1/2
    if header[:4] in (b'\x00\x00\x01\xba', b'\x00\x00\x01\xb3'):
        return True

    # MPEG-TS (sync byte 0x47 at start, and typically at offset 188)
    if header[0:1] == b'\x47' and len(header) > 188 and header[188:189] == b'\x47':
        return True

    return False


@router.post("/raw", response_model=UploadResponse)
@limiter.limit(config.RATE_LIMIT_UPLOADS)
async def upload_raw(request: Request, file: UploadFile = File(...)):
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

    # Generate job ID (128-bit) and access token
    job_id = uuid.uuid4().hex  # 32 hex chars = 128-bit entropy
    access_token = secrets.token_urlsafe(32)  # 256-bit per-job secret
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
                os.remove(file_path)
                raise HTTPException(status_code=413, detail=size_err)
            f.write(chunk)

    # Quick magic byte check before expensive ffprobe validation
    if not _check_video_magic(file_path):
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File does not appear to be a valid video (bad header)")

    # Validate video with ffprobe
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

    # Create job with access token
    job = job_manager.create_job(job_id)
    job_manager.update_job(
        job_id,
        access_token=access_token,
        raw_path=file_path,
        raw_filename=file.filename or f"video{ext}",
        duration=info["duration"],
        width=info["width"],
        height=info["height"],
        fps=info["fps"],
        file_size=total_size,
    )

    return UploadResponse(
        job_id=job_id,
        access_token=access_token,
        filename=file.filename or f"video{ext}",
        duration=round(info["duration"], 1),
        resolution=f"{info['width']}x{info['height']}",
        fps=round(info["fps"], 1),
        file_size_mb=round(total_size / (1024 * 1024), 1),
    )


@router.post("/reference", response_model=ReferenceUploadResponse)
@limiter.limit(config.RATE_LIMIT_UPLOADS)
async def upload_reference(
    request: Request,
    job_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload reference video for a job."""
    # Validate job_id format
    if not config.JOB_ID_PATTERN.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    verify_job_token(job_id, request)

    # Check disk space
    disk_err = validate_disk_space()
    if disk_err:
        raise HTTPException(status_code=507, detail=disk_err)

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
                os.remove(file_path)
                raise HTTPException(status_code=413, detail=size_err)
            f.write(chunk)

    # Quick magic byte check
    if not _check_video_magic(file_path):
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File does not appear to be a valid video (bad header)")

    # Validate video with ffprobe
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
