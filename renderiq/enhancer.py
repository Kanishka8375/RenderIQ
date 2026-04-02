"""
Video Enhancement Module (Module 2)
Auto-adjust exposure, contrast, and denoise.
All via FFmpeg video filters — no frame-by-frame processing.
"""
import subprocess
import os
import json
import logging

logger = logging.getLogger(__name__)


def enhance_video(
    video_path: str,
    output_path: str,
    auto_exposure: bool = True,
    auto_contrast: bool = True,
    denoise: bool = True,
    progress_callback=None,
) -> str:
    """
    Enhance video quality automatically.

    Uses FFmpeg filters:
    - eq: brightness/contrast/gamma adjustment
    - nlmeans: temporal denoising (light)
    - unsharp: subtle sharpening
    """
    if progress_callback:
        progress_callback("Enhancing video...", 8)

    video_filters = []

    if auto_exposure:
        # Slight gamma correction and brightness boost
        video_filters.append("eq=gamma=1.05:brightness=0.02:contrast=1.05")

    if denoise:
        # Light non-local-means denoising — removes grain without over-smoothing
        video_filters.append("nlmeans=s=3:p=7:r=9")

    if auto_contrast:
        # Subtle unsharp mask for clarity
        video_filters.append("unsharp=5:5:0.5:5:5:0.0")

    if not video_filters:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    vf = ",".join(video_filters)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.warning("Enhancement failed, using original: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)
    else:
        logger.info("Video enhanced successfully")

    if progress_callback:
        progress_callback("Enhancement complete", 12)

    return output_path


def analyze_quality(video_path: str) -> dict:
    """Analyze video quality to decide which enhancement steps are needed."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-print_format", "json", "-show_streams", video_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        stream = json.loads(r.stdout)["streams"][0]
        width = int(stream.get("width", 1920))
        height = int(stream.get("height", 1080))
        return {
            "width": width,
            "height": height,
            "is_low_res": width < 720 or height < 480,
            "needs_enhancement": True,
        }
    except Exception:
        return {"needs_enhancement": True}
