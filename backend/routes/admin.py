"""Admin endpoints for analytics and feedback."""

import json
import os
import time

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from backend.config import config
from backend.services.job_manager import job_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _verify_key(api_key: str | None):
    if api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


# --- Analytics ---

def _load_analytics() -> list[dict]:
    if os.path.isfile(config.ANALYTICS_FILE):
        with open(config.ANALYTICS_FILE) as f:
            return json.load(f)
    return []


def _save_analytics(entries: list[dict]):
    with open(config.ANALYTICS_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def log_job_analytics(
    job_id: str,
    preset: str | None,
    mode: str,
    duration: float,
    resolution: str,
    processing_time: float,
    success: bool,
):
    """Log a completed job for analytics (called from grade route)."""
    entries = _load_analytics()
    entries.append({
        "job_id": job_id,
        "timestamp": time.time(),
        "preset": preset,
        "mode": mode,
        "video_duration_s": duration,
        "resolution": resolution,
        "processing_time_s": round(processing_time, 1),
        "success": success,
    })
    _save_analytics(entries)


@router.get("/stats")
async def get_stats(x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    entries = _load_analytics()

    now = time.time()
    today_start = now - (now % 86400)
    today_entries = [e for e in entries if e["timestamp"] >= today_start]

    successful = [e for e in entries if e.get("success")]
    failed = [e for e in entries if not e.get("success")]

    preset_counts: dict[str, int] = {}
    for e in entries:
        p = e.get("preset") or "custom"
        preset_counts[p] = preset_counts.get(p, 0) + 1
    most_popular = max(preset_counts, key=preset_counts.get) if preset_counts else None

    avg_time = 0
    if successful:
        avg_time = sum(e.get("processing_time_s", 0) for e in successful) / len(successful)

    total_minutes = sum(e.get("video_duration_s", 0) for e in entries) / 60

    # Count unique IPs per day from today's entries
    today_job_ids = set(e["job_id"] for e in today_entries)

    return {
        "total_jobs": len(entries),
        "successful_jobs": len(successful),
        "failed_jobs": len(failed),
        "most_popular_preset": most_popular,
        "average_processing_time_seconds": round(avg_time, 1),
        "total_users_today": len(today_job_ids),
        "total_video_minutes_processed": round(total_minutes, 1),
    }


# --- Feedback ---

class FeedbackRequest(BaseModel):
    job_id: str
    rating: str  # "great", "ok", "bad"
    comment: str = ""


def _load_feedback() -> list[dict]:
    if os.path.isfile(config.FEEDBACK_FILE):
        with open(config.FEEDBACK_FILE) as f:
            return json.load(f)
    return []


def _save_feedback(entries: list[dict]):
    with open(config.FEEDBACK_FILE, "w") as f:
        json.dump(entries, f, indent=2)


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    entries = _load_feedback()
    entries.append({
        "job_id": req.job_id,
        "timestamp": time.time(),
        "rating": req.rating,
        "comment": req.comment,
    })
    _save_feedback(entries)
    return {"status": "ok", "message": "Thank you for your feedback!"}


@router.get("/feedback")
async def get_feedback(x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    entries = _load_feedback()
    ratings = {"great": 0, "ok": 0, "bad": 0}
    for e in entries:
        r = e.get("rating", "")
        if r in ratings:
            ratings[r] += 1
    return {
        "total": len(entries),
        "ratings": ratings,
        "entries": entries[-50:],  # Last 50
    }
