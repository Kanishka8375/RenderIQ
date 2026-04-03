"""AI Editor endpoints — prompt-driven full video editing pipeline."""

import json
import logging
import os
import sys
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.config import config
from backend.services.job_manager import job_manager
from backend.services.storage import get_job_work_dir

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-edit", tags=["ai-edit"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class AIEditRequest(BaseModel):
    job_id: str
    prompt: str = Field(min_length=1, max_length=500)


class AIEditResponse(BaseModel):
    job_id: str
    status: str
    message: str
    edit_plan: dict


# ─── Background Task ─────────────────────────────────────────────────────────

def _run_ai_edit_job(job_id: str, prompt: str):
    """Execute the full AI edit pipeline in a background thread."""
    from renderiq.prompt_parser import parse_prompt
    from renderiq.ai_editor import ai_edit

    job = job_manager.get_job(job_id)
    if not job:
        return

    work_dir = get_job_work_dir(job_id)
    edit_dir = os.path.join(work_dir, "ai_edit")
    os.makedirs(edit_dir, exist_ok=True)

    try:
        # Parse the prompt into an edit plan
        edit_plan = parse_prompt(prompt)

        job_manager.update_job(
            job_id,
            current_step="Parsed prompt, starting edit...",
            progress=2,
        )

        # Store the edit plan
        job_manager.update_job(job_id, smart_grade_info=json.dumps({
            "mode": "ai_edit",
            "prompt": prompt,
            "edit_plan": edit_plan,
        }))

        def progress_cb(step_name, pct):
            job_manager.update_job(job_id, current_step=step_name, progress=pct)

        # Run the full pipeline
        result = ai_edit(
            video_path=job.raw_path,
            edit_plan=edit_plan,
            output_dir=edit_dir,
            progress_callback=progress_cb,
        )

        # Store results
        end_time = time.time()

        # Build step summary for frontend
        ai_info = {
            "mode": "ai_edit",
            "prompt": prompt,
            "edit_plan": edit_plan,
            "steps_completed": result["steps_completed"],
            "step_details": result["step_details"],
            "processing_time": result["processing_time"],
            "color_preset": edit_plan.get("color_preset", "cinematic_warm"),
            "pacing": edit_plan.get("pacing", "medium"),
        }

        job_manager.update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="Complete",
            end_time=end_time,
            graded_video_path=result.get("output_video_path", ""),
            lut_path=result.get("output_lut_path", ""),
            preview_path=result.get("output_preview_path", ""),
            comparison_path=result.get("output_comparison_path", ""),
            smart_grade_info=json.dumps(ai_info),
        )

        # Store extra paths as job metadata
        if result.get("output_srt_path"):
            job_manager.update_job(job_id, srt_path=result["output_srt_path"])
        if result.get("output_thumbnail_path"):
            job_manager.update_job(job_id, thumbnail_path=result["output_thumbnail_path"])

        logger.info(
            "AI edit complete for job %s: %d steps in %.1fs",
            job_id, len(result["steps_completed"]), result["processing_time"],
        )

    except Exception as e:
        logger.exception("AI edit failed for job %s", job_id)
        end_time = time.time()
        error_msg = str(e) if config.DEBUG else "Processing failed. Please try again."
        job_manager.update_job(
            job_id, status="failed", error=error_msg,
            current_step=error_msg, end_time=end_time,
        )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/start", response_model=AIEditResponse)
async def start_ai_edit(request: AIEditRequest):
    """Start an AI edit job from a natural language prompt."""
    if not config.JOB_ID_PATTERN.match(request.job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    job = job_manager.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.raw_path or not os.path.isfile(job.raw_path):
        raise HTTPException(status_code=400, detail="Raw footage not uploaded yet")

    if job.status in ("processing", "queued"):
        raise HTTPException(
            status_code=409,
            detail="Job is currently processing. Wait for it to finish.",
        )

    # Parse prompt to show the user what will happen
    from renderiq.prompt_parser import parse_prompt
    edit_plan = parse_prompt(request.prompt)

    # Reset job state
    job_manager.update_job(
        request.job_id,
        status="pending",
        progress=0,
        current_step="Parsing prompt...",
        error="",
        graded_video_path="",
        preview_path="",
        comparison_path="",
        smart_grade_info="",
    )

    # Submit to job queue
    status, queue_pos = job_manager.submit_grade_task(
        request.job_id, _run_ai_edit_job, request.prompt,
    )

    message = f"AI edit started — {_count_modules(edit_plan)} modules activated"
    if status == "queued":
        message = f"Queued (position {queue_pos}). Will start automatically."

    return AIEditResponse(
        job_id=request.job_id,
        status=status,
        message=message,
        edit_plan=edit_plan,
    )


@router.get("/suggestions")
async def get_suggestions():
    """Return suggestion chips for the prompt input."""
    from renderiq.prompt_parser import get_suggestion_chips
    return {"suggestions": get_suggestion_chips()}


@router.get("/parse")
async def parse_prompt_preview(prompt: str):
    """Preview what an edit plan would look like for a given prompt (dry run)."""
    from renderiq.prompt_parser import parse_prompt
    plan = parse_prompt(prompt)
    return {
        "edit_plan": plan,
        "active_modules": _count_modules(plan),
    }


def _count_modules(plan: dict) -> int:
    """Count active modules in an edit plan."""
    module_keys = [
        "enhancement", "scene_detection", "smart_cuts", "music_sync",
        "speed_ramp", "transitions", "auto_zoom", "reframe", "captions",
    ]
    # Color grading + thumbnail always run = +2
    return sum(1 for k in module_keys if plan.get(k)) + 2
