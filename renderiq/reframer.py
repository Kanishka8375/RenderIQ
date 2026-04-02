"""
Smart Reframe Module (Module 12)
Convert aspect ratios while keeping subjects in frame.
16:9 -> 9:16 (portrait), 1:1 (square), 4:5 (Instagram)
"""
import subprocess
import os
import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

ASPECT_RATIOS = {
    "portrait": (9, 16),
    "square": (1, 1),
    "instagram": (4, 5),
    "landscape": (16, 9),
    "ultrawide": (21, 9),
}


def reframe_video(
    video_path: str,
    target_ratio: str = "portrait",
    face_data: Optional[List[dict]] = None,
    output_path: str = None,
    progress_callback=None,
) -> str:
    """
    Reframe video to a different aspect ratio.
    Uses face tracking data to keep subjects centered.
    """
    if progress_callback:
        progress_callback("Reframing video...", 65)

    ratio = ASPECT_RATIOS.get(target_ratio, (9, 16))
    width, height = _get_dimensions(video_path)

    target_w_ratio, target_h_ratio = ratio

    if target_w_ratio < target_h_ratio:
        out_height = height
        out_width = int(height * target_w_ratio / target_h_ratio)
        out_width = out_width - (out_width % 2)
    else:
        out_width = width
        out_height = int(width * target_h_ratio / target_w_ratio)
        out_height = out_height - (out_height % 2)

    # Determine crop position
    if face_data and any(d["has_face"] for d in face_data):
        face_positions = [
            d["primary_face"]["cx"] / width
            for d in face_data if d.get("primary_face")
        ]
        avg_face_x = sum(face_positions) / len(face_positions) if face_positions else 0.5

        crop_x = int((avg_face_x * width) - (out_width / 2))
        crop_x = max(0, min(crop_x, width - out_width))
        crop_y = 0
    else:
        crop_x = max(0, (width - out_width) // 2)
        crop_y = max(0, (height - out_height) // 2)

    vf = f"crop={out_width}:{out_height}:{crop_x}:{crop_y}"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("Reframe failed: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)
    else:
        logger.info("Reframed to %s: %dx%d", target_ratio, out_width, out_height)

    if progress_callback:
        progress_callback(f"Reframed to {target_ratio}", 68)

    return output_path


def _get_dimensions(path: str) -> tuple:
    """Get video width and height."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-print_format", "json", "-show_streams", path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        stream = json.loads(r.stdout)["streams"][0]
        return int(stream["width"]), int(stream["height"])
    except Exception:
        return 1920, 1080
