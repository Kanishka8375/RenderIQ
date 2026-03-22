"""File download endpoints."""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.job_manager import job_manager

router = APIRouter(prefix="/api/download", tags=["download"])


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

    base_name = os.path.splitext(job.raw_filename)[0]
    download_name = f"renderiq_graded_{base_name}.mp4"

    return FileResponse(
        job.graded_video_path,
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

    return FileResponse(
        job.lut_path,
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

    return FileResponse(
        job.preview_path,
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

    return FileResponse(
        job.comparison_path,
        media_type="image/png",
        filename="renderiq_comparison.png",
    )
