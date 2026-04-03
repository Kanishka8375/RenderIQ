"""File download endpoints."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import config
from backend.services.job_manager import job_manager

router = APIRouter(prefix="/api/download", tags=["download"])

# Directories where served files are allowed to reside
_ALLOWED_ROOTS = tuple(
    os.path.realpath(d)
    for d in (config.UPLOAD_DIR, config.OUTPUT_DIR, config.JOBS_DIR)
)


def _validate_path(path: str) -> str:
    """Resolve the path and ensure it lives under an allowed root directory."""
    real = os.path.realpath(path)
    if not any(real.startswith(root + os.sep) or real == root for root in _ALLOWED_ROOTS):
        raise HTTPException(status_code=403, detail="Access denied")
    return real


@router.get("/{job_id}/video")
async def download_video(job_id: str):
    """Serve the graded video file."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.graded_video_path or not os.path.isfile(job.graded_video_path):
        raise HTTPException(status_code=404, detail="Graded video not available")

    safe_path = _validate_path(job.graded_video_path)
    base_name = os.path.splitext(job.raw_filename)[0]
    download_name = f"renderiq_graded_{base_name}.mp4"

    return FileResponse(
        safe_path,
        media_type="video/mp4",
        filename=download_name,
    )


@router.get("/{job_id}/lut")
async def download_lut(job_id: str):
    """Serve the .cube LUT file."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.lut_path or not os.path.isfile(job.lut_path):
        raise HTTPException(status_code=404, detail="LUT file not available")

    safe_path = _validate_path(job.lut_path)
    return FileResponse(
        safe_path,
        media_type="application/octet-stream",
        filename="renderiq_grade.cube",
    )


@router.get("/{job_id}/preview")
async def download_preview(job_id: str):
    """Serve a single graded frame as PNG."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.preview_path or not os.path.isfile(job.preview_path):
        raise HTTPException(status_code=404, detail="Preview not available")

    safe_path = _validate_path(job.preview_path)
    return FileResponse(
        safe_path,
        media_type="image/png",
        filename="renderiq_preview.png",
    )


@router.get("/{job_id}/comparison")
async def download_comparison(job_id: str):
    """Serve the before/after comparison image as PNG."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.comparison_path or not os.path.isfile(job.comparison_path):
        raise HTTPException(status_code=404, detail="Comparison not available")

    safe_path = _validate_path(job.comparison_path)
    return FileResponse(
        safe_path,
        media_type="image/png",
        filename="renderiq_comparison.png",
    )


@router.get("/{job_id}/srt")
async def download_srt(job_id: str):
    """Serve the auto-generated SRT subtitles file."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.srt_path or not os.path.isfile(job.srt_path):
        raise HTTPException(status_code=404, detail="SRT file not available")

    safe_path = _validate_path(job.srt_path)
    return FileResponse(
        safe_path,
        media_type="text/plain",
        filename="renderiq_captions.srt",
    )


@router.get("/{job_id}/thumbnail")
async def download_thumbnail(job_id: str):
    """Serve the auto-generated thumbnail."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.thumbnail_path or not os.path.isfile(job.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    safe_path = _validate_path(job.thumbnail_path)
    return FileResponse(
        safe_path,
        media_type="image/jpeg",
        filename="renderiq_thumbnail.jpg",
    )
