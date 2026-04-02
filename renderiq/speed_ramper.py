"""
Speed Ramp Module (Module 9)
Auto slow-motion on highlights, speed up on boring parts.
Uses scene interest scores + beat data to decide.
"""
import subprocess
import os
import logging
from typing import List

logger = logging.getLogger(__name__)


def apply_speed_ramp(
    video_path: str,
    scenes: List[dict],
    beats: List[float] = None,
    pacing: str = "medium",
    output_path: str = None,
    progress_callback=None,
) -> str:
    """
    Apply variable speed to video based on scene interest.

    Speed rules:
    - High interest scenes (>0.7): slow down (emphasis)
    - Medium interest (0.4-0.7): normal speed
    - Low interest (<0.4): speed up
    """
    if progress_callback:
        progress_callback("Applying speed effects...", 42)

    if not scenes:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    speed_config = {
        "slow": {"highlight": 0.5, "normal": 1.0, "boring": 1.3},
        "medium": {"highlight": 0.7, "normal": 1.0, "boring": 1.5},
        "fast": {"highlight": 0.8, "normal": 1.2, "boring": 2.0},
    }

    config = speed_config.get(pacing, speed_config["medium"])

    temp_dir = os.path.dirname(output_path)
    segment_files = []
    concat_list_path = os.path.join(temp_dir, "speed_concat.txt")

    for i, scene in enumerate(scenes):
        interest = scene.get("interest_score", 0.5)

        if interest > 0.7:
            speed = config["highlight"]
        elif interest < 0.4:
            speed = config["boring"]
        else:
            speed = config["normal"]

        if 0.9 <= speed <= 1.1:
            speed = 1.0

        scene["applied_speed"] = speed

        seg_path = os.path.join(temp_dir, f"seg_{i:04d}.mp4")

        start = scene["start_time"]
        duration = scene["duration"]

        video_speed = f"setpts={1/speed}*PTS"

        if 0.5 < speed <= 2.0:
            audio_speed = f"atempo={speed}"
        elif speed <= 0.5:
            audio_speed = f"atempo={speed*2},atempo=0.5"
        else:
            audio_speed = f"atempo=2.0,atempo={speed/2}"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-vf", video_speed,
            "-af", audio_speed,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            seg_path,
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if os.path.exists(seg_path) and os.path.getsize(seg_path) > 100:
            segment_files.append(seg_path)

    if not segment_files:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    with open(concat_list_path, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)

    # Cleanup temp files
    for seg in segment_files:
        try:
            os.remove(seg)
        except OSError:
            pass
    try:
        os.remove(concat_list_path)
    except OSError:
        pass

    if result.returncode != 0:
        logger.warning("Speed ramp concat failed: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)

    speed_changes = sum(1 for s in scenes if s.get("applied_speed", 1.0) != 1.0)
    logger.info("Speed ramp: %d/%d scenes modified", speed_changes, len(scenes))

    if progress_callback:
        progress_callback(f"Speed effects applied ({speed_changes} changes)", 48)

    return output_path
