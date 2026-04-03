"""
AI Editor Master Pipeline
Orchestrates all 14 modules in the correct order to produce
a fully AI-edited video from a single natural language prompt.
"""
import logging
import os
import shutil
import time
from typing import Optional

logger = logging.getLogger(__name__)


def ai_edit(
    video_path: str,
    edit_plan: dict,
    output_dir: str,
    progress_callback=None,
) -> dict:
    """
    Full 14-module AI editing pipeline.

    Args:
        video_path: Path to the input video.
        edit_plan: Dict from prompt_parser.parse_prompt().
        output_dir: Directory for intermediate and final output files.
        progress_callback: Optional fn(step_name: str, progress: int).

    Returns:
        Dict with output paths, steps completed, and metadata.
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    current_video = video_path
    steps_completed = []
    step_details = {}

    def cb(msg, pct):
        if progress_callback:
            progress_callback(msg, pct)

    # ─── PRE-PROCESSING ──────────────────────────────────────────────

    # Module 7: Audio Clean
    if edit_plan.get("enhancement", False):
        try:
            from renderiq.audio_cleaner import clean_audio
            cleaned_path = os.path.join(output_dir, "audio_cleaned.mp4")
            result_path = clean_audio(current_video, cleaned_path, progress_callback=cb)
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("audio_clean")
            step_details["audio_clean"] = "Noise removed, volume normalized"
        except Exception as e:
            logger.warning("Audio clean failed: %s", e)

    # Module 2: Video Enhancement
    if edit_plan.get("enhancement", False):
        try:
            from renderiq.enhancer import enhance_video
            enhanced_path = os.path.join(output_dir, "enhanced.mp4")
            result_path = enhance_video(current_video, enhanced_path, progress_callback=cb)
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("enhancement")
            step_details["enhancement"] = "Exposure + contrast fixed"
        except Exception as e:
            logger.warning("Enhancement failed: %s", e)

    # ─── ANALYSIS ────────────────────────────────────────────────────

    # Module 3: Scene Detection
    scenes = []
    if edit_plan.get("scene_detection", True):
        try:
            from renderiq.scene_detector import detect_scenes
            scenes = detect_scenes(current_video, progress_callback=cb)
            steps_completed.append("scene_detection")
            step_details["scene_detection"] = f"{len(scenes)} scenes detected"
        except Exception as e:
            logger.warning("Scene detection failed: %s", e)

    # Module 8: Face Tracking
    face_data = []
    needs_face = edit_plan.get("auto_zoom") or edit_plan.get("reframe")
    if needs_face or scenes:
        try:
            from renderiq.face_tracker import track_faces
            face_data = track_faces(current_video, progress_callback=cb)
            face_count = sum(1 for d in face_data if d["has_face"])
            steps_completed.append("face_tracking")
            step_details["face_tracking"] = f"Tracked across {face_count} frames"
        except Exception as e:
            logger.warning("Face tracking failed: %s", e)

    # ─── EDITING ─────────────────────────────────────────────────────

    # Module 4: Smart Cuts
    if edit_plan.get("smart_cuts", False) and scenes:
        try:
            from renderiq.smart_cutter import smart_cut
            cut_path = os.path.join(output_dir, "cut.mp4")
            cut_result = smart_cut(
                current_video, scenes,
                pacing=edit_plan.get("pacing", "medium"),
                output_path=cut_path,
                progress_callback=cb,
            )
            if os.path.exists(cut_path) and os.path.getsize(cut_path) > 100:
                current_video = cut_path
                scenes = cut_result.get("kept_scenes", scenes)
            steps_completed.append("smart_cuts")
            kept = len(cut_result.get("kept_scenes", scenes))
            step_details["smart_cuts"] = f"Kept {kept}/{len(scenes)} scenes"
        except Exception as e:
            logger.warning("Smart cuts failed: %s", e)

    # Module 5: Music Sync
    if edit_plan.get("music_sync", False) and scenes:
        try:
            from renderiq.music_sync import detect_beats, sync_cuts_to_beats
            beats = detect_beats(current_video, progress_callback=cb)
            if beats:
                scenes = sync_cuts_to_beats(scenes, beats)
                from renderiq.smart_cutter import _assemble_cuts
                synced_path = os.path.join(output_dir, "synced.mp4")
                _assemble_cuts(current_video, scenes, synced_path)
                if os.path.exists(synced_path) and os.path.getsize(synced_path) > 100:
                    current_video = synced_path
                steps_completed.append("music_sync")
                step_details["music_sync"] = f"Synced to {len(beats)} beats"
        except Exception as e:
            logger.warning("Music sync failed: %s", e)

    # Module 9: Speed Ramp
    if edit_plan.get("speed_ramp", False) and scenes:
        try:
            from renderiq.speed_ramper import apply_speed_ramp
            speed_path = os.path.join(output_dir, "speed_ramped.mp4")
            result_path = apply_speed_ramp(
                current_video, scenes,
                pacing=edit_plan.get("pacing", "medium"),
                output_path=speed_path,
                progress_callback=cb,
            )
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            speed_changes = sum(1 for s in scenes if s.get("applied_speed", 1.0) != 1.0)
            steps_completed.append("speed_ramp")
            step_details["speed_ramp"] = f"{speed_changes} scenes speed-adjusted"
        except Exception as e:
            logger.warning("Speed ramp failed: %s", e)

    # Module 10: Transitions
    if edit_plan.get("transitions", False) and scenes:
        try:
            from renderiq.transitions import add_transitions
            trans_path = os.path.join(output_dir, "transitions.mp4")
            result_path = add_transitions(
                current_video, scenes,
                pacing=edit_plan.get("pacing", "medium"),
                output_path=trans_path,
                progress_callback=cb,
            )
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("transitions")
            step_details["transitions"] = f"{max(0, len(scenes)-1)} crossfades added"
        except Exception as e:
            logger.warning("Transitions failed: %s", e)

    # ─── VISUAL FX ───────────────────────────────────────────────────

    # Module 1: Color Grading — ALWAYS RUNS
    lut_path = os.path.join(output_dir, "grade.cube")
    try:
        from renderiq.presets_builder import get_preset_path
        from renderiq.lut_generator import load_cube, export_cube
        from renderiq.grader import apply_lut_to_video

        preset_name = edit_plan.get("color_preset", "cinematic_warm")
        strength = edit_plan.get("color_strength", 0.8)

        preset_path = get_preset_path(preset_name)
        lut = load_cube(preset_path)
        export_cube(lut, lut_path)

        graded_path = os.path.join(output_dir, "graded.mp4")

        def grade_progress(pct):
            cb(f"Color grading ({preset_name})...", 55 + int(pct * 0.1))

        apply_lut_to_video(
            current_video, lut, graded_path,
            strength=strength,
            progress_callback=grade_progress,
        )
        if os.path.exists(graded_path) and os.path.getsize(graded_path) > 100:
            current_video = graded_path
        steps_completed.append("color_grading")
        step_details["color_grading"] = f"{preset_name.replace('_', ' ').title()} at {int(strength*100)}%"
    except Exception as e:
        logger.warning("Color grading failed: %s", e)

    # Module 11: Auto Zoom
    if edit_plan.get("auto_zoom", False) and scenes:
        try:
            from renderiq.auto_zoom import apply_auto_zoom
            zoom_path = os.path.join(output_dir, "zoomed.mp4")
            result_path = apply_auto_zoom(
                current_video, scenes, face_data=face_data,
                output_path=zoom_path, progress_callback=cb,
            )
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("auto_zoom")
            step_details["auto_zoom"] = "Ken Burns zoom effects applied"
        except Exception as e:
            logger.warning("Auto zoom failed: %s", e)

    # Module 12: Reframe
    if edit_plan.get("reframe", False):
        try:
            from renderiq.reframer import reframe_video
            reframe_path = os.path.join(output_dir, "reframed.mp4")
            target = edit_plan.get("reframe_ratio", "portrait")
            result_path = reframe_video(
                current_video, target_ratio=target,
                face_data=face_data, output_path=reframe_path,
                progress_callback=cb,
            )
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("reframe")
            step_details["reframe"] = f"Reframed to {target}"
        except Exception as e:
            logger.warning("Reframe failed: %s", e)

    # ─── OVERLAY ─────────────────────────────────────────────────────

    # Module 6: Auto Captions
    srt_path = os.path.join(output_dir, "captions.srt")
    if edit_plan.get("captions", False):
        try:
            from renderiq.captioner import generate_subtitles, burn_captions
            generate_subtitles(current_video, srt_path, progress_callback=cb)
            if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
                captioned_path = os.path.join(output_dir, "captioned.mp4")
                burn_captions(
                    current_video, srt_path, captioned_path,
                    style=edit_plan.get("caption_style", "bold"),
                    progress_callback=cb,
                )
                if os.path.exists(captioned_path) and os.path.getsize(captioned_path) > 100:
                    current_video = captioned_path
                steps_completed.append("auto_captions")
                # Count SRT segments
                with open(srt_path) as f:
                    seg_count = f.read().count("\n\n")
                step_details["auto_captions"] = f"{seg_count} caption segments"
        except Exception as e:
            logger.warning("Auto captions failed: %s", e)

    # Module 13: Text/Titles
    if edit_plan.get("title") or edit_plan.get("end_text"):
        try:
            from renderiq.text_overlay import add_text_overlays
            titled_path = os.path.join(output_dir, "titled.mp4")
            result_path = add_text_overlays(
                current_video, titled_path,
                title=edit_plan.get("title"),
                subtitle=edit_plan.get("subtitle"),
                end_text=edit_plan.get("end_text"),
                progress_callback=cb,
            )
            if result_path and os.path.exists(result_path) and os.path.getsize(result_path) > 100:
                current_video = result_path
            steps_completed.append("text_overlays")
            step_details["text_overlays"] = "Title/end card added"
        except Exception as e:
            logger.warning("Text overlays failed: %s", e)

    # Module 14: Thumbnail — ALWAYS RUNS
    thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
    try:
        from renderiq.thumbnail_gen import generate_thumbnail
        generate_thumbnail(
            current_video, scenes, face_data,
            title_text=edit_plan.get("title"),
            output_path=thumbnail_path,
            progress_callback=cb,
        )
        steps_completed.append("thumbnail")
        step_details["thumbnail"] = "Best frame selected"
    except Exception as e:
        logger.warning("Thumbnail generation failed: %s", e)

    # ─── FINAL OUTPUT ────────────────────────────────────────────────

    cb("Finalizing...", 96)

    final_path = os.path.join(output_dir, "final.mp4")
    if os.path.exists(current_video) and current_video != final_path:
        shutil.copy2(current_video, final_path)
    elif not os.path.exists(final_path):
        shutil.copy2(video_path, final_path)

    # Generate comparison
    comparison_path = os.path.join(output_dir, "comparison.png")
    preview_path = os.path.join(output_dir, "preview.png")
    try:
        from renderiq.grader import preview_grade
        from renderiq.comparison import create_comparison
        from renderiq.lut_generator import load_cube
        import cv2

        preset_name = edit_plan.get("color_preset", "cinematic_warm")
        from renderiq.presets_builder import get_preset_path
        lut = load_cube(get_preset_path(preset_name))
        original, graded = preview_grade(
            video_path, lut, strength=edit_plan.get("color_strength", 0.8),
        )
        cv2.imwrite(preview_path, cv2.cvtColor(graded, cv2.COLOR_RGB2BGR))
        comp = create_comparison(original, graded, mode="side_by_side")
        cv2.imwrite(comparison_path, cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))
    except Exception as e:
        logger.warning("Preview/comparison generation failed: %s", e)

    elapsed = time.time() - start_time

    cb("AI edit complete", 100)

    return {
        "output_video_path": final_path,
        "output_lut_path": lut_path if os.path.exists(lut_path) else None,
        "output_srt_path": srt_path if "auto_captions" in steps_completed else None,
        "output_thumbnail_path": thumbnail_path if os.path.exists(thumbnail_path) else None,
        "output_preview_path": preview_path if os.path.exists(preview_path) else None,
        "output_comparison_path": comparison_path if os.path.exists(comparison_path) else None,
        "steps_completed": steps_completed,
        "step_details": step_details,
        "edit_plan": edit_plan,
        "processing_time": round(elapsed, 2),
    }
