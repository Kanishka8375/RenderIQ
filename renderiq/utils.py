"""Helper functions for video info, file handling, and validation."""

import json
import os
import subprocess


SUPPORTED_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]


def get_video_info(video_path: str) -> dict:
    """Returns duration, fps, resolution, codec, has_audio, file_size.

    Uses FFprobe to extract video metadata.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)

    video_stream = None
    has_audio = False
    for stream in probe.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio":
            has_audio = True

    if video_stream is None:
        raise ValueError(f"No video stream found in: {video_path}")

    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", video_stream.get("duration", 0)))
    fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) != 0 else 30.0

    return {
        "duration": duration,
        "fps": fps,
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "codec": video_stream.get("codec_name", "unknown"),
        "has_audio": has_audio,
        "file_size": int(fmt.get("size", 0)),
    }


def validate_video(video_path: str) -> bool:
    """Check if file exists, is a valid video format, and not corrupted."""
    if not os.path.isfile(video_path):
        return False

    ext = os.path.splitext(video_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        return False

    try:
        get_video_info(video_path)
        return True
    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
        return False


def supported_formats() -> list[str]:
    """Returns list of supported video formats: mp4, mov, avi, mkv, webm."""
    return [fmt.lstrip(".") for fmt in SUPPORTED_FORMATS]
