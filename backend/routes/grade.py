"""Grading job endpoints."""

import json
import logging
import os
import sys
import time

from fastapi import APIRouter, HTTPException

from backend.config import config
from backend.models.schemas import GradeRequest, GradeStartResponse, GradeStatusResponse
from backend.services.job_manager import job_manager
from backend.services.storage import get_job_work_dir

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grade", tags=["grade"])


def _run_grade_job(job_id: str, request: GradeRequest):
    """Execute grading in background thread."""
    from renderiq.sampler import extract_keyframes
    from renderiq.analyzer import analyze_color_profile, cluster_keyframes
    from renderiq.lut_generator import generate_lut, export_cube, load_cube
    from renderiq.grader import (
        apply_lut_to_video, apply_multi_scene_lut, preview_grade,
    )
    from renderiq.comparison import create_comparison
    from renderiq.presets_builder import get_preset_path
    import cv2

    job = job_manager.get_job(job_id)
    if not job:
        return

    work_dir = get_job_work_dir(job_id)

    try:
        # Step 1: Extract keyframes from reference or load preset
        job_manager.update_job(job_id, current_step="Preparing color grade...", progress=5)

        if request.mode == "preset":
            # Load preset LUT directly
            job_manager.update_job(job_id, current_step="Loading preset...", progress=10)
            preset_path = get_preset_path(request.preset_name)
            lut = load_cube(preset_path)
            lut_path = preset_path
            luts = None
            cluster_profiles = None
        else:
            # Reference-based grading
            ref_path = job.reference_path
            if not ref_path or not os.path.isfile(ref_path):
                raise FileNotFoundError("Reference video not found")

            job_manager.update_job(job_id, current_step="Extracting keyframes...", progress=5)
            ref_keyframes = extract_keyframes(ref_path)

            job_manager.update_job(job_id, current_step="Analyzing colors...", progress=15)

            if request.multi_scene:
                clusters = cluster_keyframes(ref_keyframes, n_clusters=3)
                cluster_profiles = [analyze_color_profile(c) for c in clusters]
                ref_profile = cluster_profiles[0]
            else:
                ref_profile = analyze_color_profile(ref_keyframes)
                cluster_profiles = None

            # Analyze raw footage
            job_manager.update_job(job_id, current_step="Analyzing raw footage...", progress=20)
            raw_keyframes = extract_keyframes(job.raw_path)
            src_profile = analyze_color_profile(raw_keyframes)

            job_manager.update_job(job_id, current_step="Generating LUT...", progress=25)

            if request.multi_scene and cluster_profiles:
                luts = [generate_lut(src_profile, cp) for cp in cluster_profiles]
                lut = luts[0]
            else:
                lut = generate_lut(src_profile, ref_profile)
                luts = None

            # Export LUT
            lut_path = os.path.join(work_dir, "grade.cube")
            export_cube(lut, lut_path)

        # Step 2: Apply LUT to video
        want_video = request.output_format in ("video", "both")
        want_lut = request.output_format in ("lut", "both")

        graded_video_path = ""
        if want_video:
            job_manager.update_job(job_id, current_step="Applying grade to video...", progress=30)
            graded_video_path = os.path.join(work_dir, "graded.mp4")

            if request.multi_scene and luts and cluster_profiles:
                apply_multi_scene_lut(
                    job.raw_path, luts, cluster_profiles, graded_video_path,
                    strength=request.strength, auto_wb=request.auto_wb,
                )
            else:
                apply_lut_to_video(
                    job.raw_path, lut, graded_video_path,
                    strength=request.strength, auto_wb=request.auto_wb,
                )

        job_manager.update_job(job_id, current_step="Generating preview...", progress=90)

        # Step 3: Generate preview and comparison
        original, graded = preview_grade(
            job.raw_path, lut, strength=request.strength
        )

        preview_path = os.path.join(work_dir, "preview.png")
        cv2.imwrite(preview_path, cv2.cvtColor(graded, cv2.COLOR_RGB2BGR))

        comparison_path = os.path.join(work_dir, "comparison.png")
        comp = create_comparison(original, graded, mode="side_by_side")
        cv2.imwrite(comparison_path, cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))

        # Save LUT if requested
        final_lut_path = ""
        if want_lut:
            if request.mode == "preset":
                final_lut_path = lut_path
            else:
                final_lut_path = lut_path

        end_time = time.time()
        job_manager.update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="Complete",
            end_time=end_time,
            graded_video_path=graded_video_path,
            lut_path=final_lut_path,
            preview_path=preview_path,
            comparison_path=comparison_path,
        )

        # Log analytics
        try:
            from backend.routes.admin import log_job_analytics
            log_job_analytics(
                job_id=job_id,
                preset=request.preset_name,
                mode=request.mode,
                duration=job.duration,
                resolution=f"{job.width}x{job.height}",
                processing_time=end_time - job.start_time,
                success=True,
            )
        except Exception:
            logger.warning("Failed to log analytics for job %s", job_id)

    except Exception as e:
        logger.exception("Grading failed for job %s", job_id)
        end_time = time.time()
        job_manager.update_job(
            job_id, status="failed", error=str(e),
            current_step=f"Error: {e}", end_time=end_time,
        )
        try:
            from backend.routes.admin import log_job_analytics
            log_job_analytics(
                job_id=job_id,
                preset=request.preset_name,
                mode=request.mode,
                duration=job.duration,
                resolution=f"{job.width}x{job.height}",
                processing_time=end_time - (job.start_time or end_time),
                success=False,
            )
        except Exception:
            pass


def _run_smart_grade_job(job_id: str, request: GradeRequest):
    """Execute smart grading (audio+visual mood analysis) in background thread."""
    from renderiq.smart_grade import smart_grade
    from renderiq.grader import preview_grade
    from renderiq.comparison import create_comparison
    from renderiq.lut_generator import export_cube, load_cube
    import cv2

    job = job_manager.get_job(job_id)
    if not job:
        return

    work_dir = get_job_work_dir(job_id)

    try:
        graded_video_path = os.path.join(work_dir, "graded.mp4")

        def progress_cb(step_name, pct):
            job_manager.update_job(job_id, current_step=step_name, progress=pct)

        result = smart_grade(
            video_path=job.raw_path,
            output_path=graded_video_path,
            strength_override=request.strength if request.strength != 0.8 else None,
            progress_callback=progress_cb,
        )

        # Store smart grade analysis info
        smart_info = {
            "mood": result["mood_profile"]["mood"],
            "audio_mood": result["audio_analysis"]["mood"],
            "visual_scene": result["visual_analysis"]["scene_type"],
            "has_faces": result["visual_analysis"]["has_faces"],
            "preset_applied": result["grade_applied"]["preset"],
            "strength_applied": result["grade_applied"]["strength"],
            "description": result["grade_applied"]["description"],
            "confidence": result["mood_profile"]["confidence"],
            "mood_tags": result["mood_profile"].get("mood_tags", []),
            "processing_time": result["processing_time"],
        }
        job_manager.update_job(job_id, smart_grade_info=json.dumps(smart_info))

        # Generate preview and comparison from the applied preset
        job_manager.update_job(job_id, current_step="Generating preview...", progress=90)
        from renderiq.presets_builder import get_preset_path
        preset_name = result["grade_applied"]["preset"]
        preset_path = get_preset_path(preset_name)
        lut = load_cube(preset_path)

        original, graded = preview_grade(
            job.raw_path, lut, strength=result["grade_applied"]["strength"],
        )

        preview_path = os.path.join(work_dir, "preview.png")
        cv2.imwrite(preview_path, cv2.cvtColor(graded, cv2.COLOR_RGB2BGR))

        comparison_path = os.path.join(work_dir, "comparison.png")
        comp = create_comparison(original, graded, mode="side_by_side")
        cv2.imwrite(comparison_path, cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))

        # Export LUT
        lut_path = os.path.join(work_dir, "grade.cube")
        export_cube(lut, lut_path)

        end_time = time.time()
        job_manager.update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="Complete",
            end_time=end_time,
            graded_video_path=graded_video_path,
            lut_path=lut_path,
            preview_path=preview_path,
            comparison_path=comparison_path,
        )

        try:
            from backend.routes.admin import log_job_analytics
            log_job_analytics(
                job_id=job_id,
                preset=result["grade_applied"]["preset"],
                mode="smart",
                duration=job.duration,
                resolution=f"{job.width}x{job.height}",
                processing_time=end_time - job.start_time,
                success=True,
            )
        except Exception:
            logger.warning("Failed to log analytics for job %s", job_id)

    except Exception as e:
        logger.exception("Smart grading failed for job %s", job_id)
        end_time = time.time()
        job_manager.update_job(
            job_id, status="failed", error=str(e),
            current_step=f"Error: {e}", end_time=end_time,
        )


@router.post("/start", response_model=GradeStartResponse)
async def start_grade(request: GradeRequest):
    """Start a grading job in the background."""
    job = job_manager.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {request.job_id}")

    if not job.raw_path or not os.path.isfile(job.raw_path):
        raise HTTPException(status_code=400, detail="Raw footage not uploaded yet")

    if request.mode == "reference":
        if not job.reference_path or not os.path.isfile(job.reference_path):
            raise HTTPException(status_code=400, detail="Reference video not uploaded yet")

    if request.mode == "preset" and not request.preset_name:
        raise HTTPException(status_code=400, detail="Preset name required for preset mode")

    # Choose task function based on mode
    task_fn = _run_smart_grade_job if request.mode == "smart" else _run_grade_job

    # Submit to job queue
    status, queue_pos = job_manager.submit_grade_task(
        request.job_id, task_fn, request
    )

    message = "Grading started"
    if status == "queued":
        message = f"Queued (position {queue_pos}). Will start automatically."

    return GradeStartResponse(
        job_id=request.job_id,
        status=status,
        message=message,
    )


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get current job status."""
    status = job_manager.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return status
