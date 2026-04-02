"""
Transitions Module (Module 10)
Add cinematic transitions between scene cuts.
AI selects transition type based on content mood.
"""
import subprocess
import os
import json
import logging
import shutil
from typing import List

logger = logging.getLogger(__name__)

TRANSITION_DURATION = {
    "slow": 1.0,
    "medium": 0.5,
    "fast": 0.3,
}


def add_transitions(
    video_path: str,
    scenes: List[dict],
    pacing: str = "medium",
    output_path: str = None,
    progress_callback=None,
) -> str:
    """
    Add transitions between scene cuts.
    Uses FFmpeg xfade filter for crossfade/dissolve effects.
    """
    if progress_callback:
        progress_callback("Adding transitions...", 50)

    if len(scenes) < 2:
        shutil.copy2(video_path, output_path)
        return output_path

    trans_duration = TRANSITION_DURATION.get(pacing, 0.5)
    temp_dir = os.path.dirname(output_path)

    # Extract individual scenes
    scene_clips = []
    for i, scene in enumerate(scenes):
        clip_path = os.path.join(temp_dir, f"trans_clip_{i:04d}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(scene["start_time"]),
            "-i", video_path,
            "-t", str(scene["duration"]),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            clip_path,
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if os.path.exists(clip_path) and os.path.getsize(clip_path) > 100:
            scene_clips.append(clip_path)

    if len(scene_clips) < 2:
        shutil.copy2(video_path, output_path)
        return output_path

    # Apply xfade transitions sequentially
    current = scene_clips[0]

    for i in range(1, len(scene_clips)):
        next_clip = scene_clips[i]
        temp_output = os.path.join(temp_dir, f"trans_merged_{i:04d}.mp4")

        current_duration = _get_clip_duration(current)
        offset = max(0, current_duration - trans_duration)

        transition = _select_transition(scenes[i] if i < len(scenes) else None)

        if transition == "fade_black":
            xfade = f"xfade=transition=fade:duration={trans_duration}:offset={offset}"
        elif transition == "fade_white":
            xfade = f"xfade=transition=wiperight:duration={trans_duration}:offset={offset}"
        else:
            xfade = f"xfade=transition=fade:duration={trans_duration}:offset={offset}"

        acrossfade = f"acrossfade=d={trans_duration}"

        cmd = [
            "ffmpeg", "-y",
            "-i", current,
            "-i", next_clip,
            "-filter_complex",
            f"[0:v][1:v]{xfade}[v];[0:a][1:a]{acrossfade}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            temp_output,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and os.path.exists(temp_output):
            current = temp_output
        else:
            logger.warning("Transition %d failed, skipping", i)

    if os.path.exists(current):
        shutil.copy2(current, output_path)
    else:
        shutil.copy2(video_path, output_path)

    # Cleanup
    for clip in scene_clips:
        try:
            os.remove(clip)
        except OSError:
            pass

    if progress_callback:
        progress_callback("Transitions added", 55)

    return output_path


def _select_transition(scene: dict) -> str:
    """Select transition type based on scene characteristics."""
    if not scene:
        return "crossfade"

    motion = scene.get("motion_score", 0.5)
    brightness = scene.get("brightness", 0.5)

    if motion > 0.6:
        return "crossfade"
    if brightness < 0.3:
        return "fade_black"
    if brightness > 0.8:
        return "fade_white"

    return "crossfade"


def _get_clip_duration(path: str) -> float:
    """Get video duration."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 5.0
