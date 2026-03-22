"""Helper functions for video info, file handling, and validation."""

import json
import os
import subprocess


SUPPORTED_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]


def get_video_info(video_path: str) -> dict:
    """Returns duration, fps, resolution, codec, has_audio, audio_streams, file_size.

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
    audio_stream_count = 0
    has_audio = False
    for stream in probe.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio":
            has_audio = True
            audio_stream_count += 1

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
        "audio_streams": audio_stream_count,
        "file_size": int(fmt.get("size", 0)),
    }


def validate_video(video_path: str) -> dict | bool:
    """Check if file is a valid video. Returns dict with details or False.

    Checks:
    - File exists and is readable
    - Has at least one video stream
    - Duration is greater than 0
    - Can decode at least the first frame without error

    Returns:
        dict with 'valid' bool and 'error' string if invalid,
        or True for backward compatibility when valid.
    """
    if not os.path.isfile(video_path):
        return {"valid": False, "error": f"File not found: {video_path}"}

    if os.path.getsize(video_path) == 0:
        return {"valid": False, "error": f"File is empty (zero bytes): {video_path}"}

    ext = os.path.splitext(video_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        return {"valid": False, "error": f"Unsupported format '{ext}'. Supported: {', '.join(SUPPORTED_FORMATS)}"}

    try:
        info = get_video_info(video_path)
    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as e:
        return {"valid": False, "error": f"Cannot read video metadata: {e}"}

    if info["duration"] <= 0:
        return {"valid": False, "error": f"Video has invalid duration: {info['duration']}"}

    # Try to decode the first frame
    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-i", video_path,
            "-vframes", "1",
            "-f", "null", "-"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return {"valid": False, "error": f"Cannot decode first frame: {proc.stderr.strip()}"}
    except subprocess.TimeoutExpired:
        return {"valid": False, "error": "Timed out trying to decode first frame"}

    return True


def supported_formats() -> list[str]:
    """Returns list of supported video formats: mp4, mov, avi, mkv, webm."""
    return [fmt.lstrip(".") for fmt in SUPPORTED_FORMATS]


def check_gpu_available() -> bool:
    """Check if NVIDIA GPU encoding is available via FFmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        return "h264_nvenc" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
