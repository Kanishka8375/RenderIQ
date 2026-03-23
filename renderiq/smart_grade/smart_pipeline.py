"""Smart Grade Pipeline — orchestrates audio + visual analysis and grading."""

import logging
import os
import time

from renderiq.smart_grade.audio_analyzer import (
    extract_audio, analyze_music_features, classify_audio_mood,
)
from renderiq.smart_grade.visual_analyzer import analyze_visual_content
from renderiq.smart_grade.mood_engine import compute_mood_profile

logger = logging.getLogger(__name__)

# Default presets directory
_DEFAULT_PRESETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "presets", "builtin",
)


def smart_grade(
    video_path: str,
    output_path: str,
    presets_dir: str | None = None,
    strength_override: float | None = None,
    preset_override: str | None = None,
    progress_callback=None,
) -> dict:
    """Full smart grade pipeline: analyze audio + visuals, pick grade, apply.

    Args:
        video_path: Path to raw footage.
        output_path: Where to save graded video.
        presets_dir: Directory containing .cube preset files.
        strength_override: If set, overrides auto-detected strength.
        preset_override: If set, overrides auto-detected preset.
        progress_callback: Optional fn(step_name, progress_pct) for updates.

    Returns:
        Dict with output_path, mood_profile, audio/visual analysis,
        grade_applied info, processing_time, and step timings.
    """
    from renderiq.sampler import extract_keyframes
    from renderiq.grader import apply_lut_to_video
    from renderiq.presets_builder import get_preset_path

    if presets_dir is None:
        presets_dir = _DEFAULT_PRESETS_DIR

    start = time.time()
    steps = []

    def _progress(step, pct):
        if progress_callback:
            progress_callback(step, pct)

    # Step 1: Extract keyframes
    _progress("Extracting keyframes...", 5)
    step_start = time.time()
    keyframes = extract_keyframes(video_path, max_frames=50)
    steps.append({"step": "keyframe_extraction", "time": round(time.time() - step_start, 2)})

    # Step 2: Extract and analyze audio
    _progress("Analyzing audio mood...", 15)
    step_start = time.time()
    audio_path = None
    try:
        audio_path = extract_audio(video_path)
        audio_features = analyze_music_features(audio_path)
        audio_mood = classify_audio_mood(audio_features)
    except Exception as e:
        logger.info("Audio analysis skipped: %s", e)
        audio_features = {"has_audio": False}
        audio_mood = {
            "primary_mood": "neutral",
            "secondary_mood": "calm",
            "intensity": 0.3,
            "warmth": 0.5,
            "complexity": 0.2,
            "mood_tags": ["no_audio"],
        }
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    steps.append({"step": "audio_analysis", "time": round(time.time() - step_start, 2)})

    # Step 3: Analyze visual content
    _progress("Analyzing visual content...", 30)
    step_start = time.time()
    visual_analysis = analyze_visual_content(keyframes)
    steps.append({"step": "visual_analysis", "time": round(time.time() - step_start, 2)})

    # Step 4: Compute mood profile
    _progress("Computing mood profile...", 40)
    step_start = time.time()
    mood_profile = compute_mood_profile(audio_mood, visual_analysis)
    steps.append({"step": "mood_computation", "time": round(time.time() - step_start, 2)})

    # Step 5: Determine preset and strength
    preset = preset_override or mood_profile["recommended_preset"]
    strength = (
        strength_override
        if strength_override is not None
        else mood_profile["recommended_strength"]
    )

    # Resolve preset path
    preset_path = os.path.join(presets_dir, f"{preset}.cube")
    if not os.path.exists(preset_path):
        # Fallback: try generating it
        preset_path = get_preset_path(preset)

    # Step 6: Apply grade
    _progress("Applying color grade...", 50)
    step_start = time.time()
    apply_lut_to_video(video_path, preset_path, output_path, strength=strength)
    steps.append({"step": "grading", "time": round(time.time() - step_start, 2)})

    total_time = time.time() - start

    return {
        "output_path": output_path,
        "mood_profile": mood_profile,
        "audio_analysis": {
            "has_audio": audio_features.get("has_audio", False),
            "tempo": audio_features.get("tempo"),
            "energy": audio_features.get("energy"),
            "mood": audio_mood.get("primary_mood"),
        },
        "visual_analysis": {
            "scene_type": visual_analysis.get("scene_type"),
            "brightness": visual_analysis.get("brightness"),
            "has_faces": visual_analysis.get("has_faces"),
            "motion_level": visual_analysis.get("motion_level"),
        },
        "grade_applied": {
            "preset": preset,
            "strength": strength,
            "description": mood_profile.get("grade_description"),
            "was_overridden": preset_override is not None or strength_override is not None,
        },
        "processing_time": round(total_time, 2),
        "steps": steps,
    }
