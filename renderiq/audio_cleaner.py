"""
Audio Clean Module (Module 7)
Remove background noise, normalize volume, enhance voice.
All via FFmpeg audio filters — no frame-by-frame processing.
"""
import subprocess
import os
import json
import logging
import re

logger = logging.getLogger(__name__)


def clean_audio(
    video_path: str,
    output_path: str,
    remove_noise: bool = True,
    normalize_volume: bool = True,
    enhance_voice: bool = True,
    progress_callback=None,
) -> str:
    """
    Clean and enhance audio in a video file.

    Uses FFmpeg audio filters:
    - afftdn: Adaptive noise reduction (removes hiss, hum, background noise)
    - loudnorm: EBU R128 loudness normalization (consistent volume)
    - highpass + lowpass: Voice frequency isolation (cut below 80Hz, above 13kHz)
    - acompressor: Light compression to even out voice dynamics
    """
    if progress_callback:
        progress_callback("Cleaning audio...", 3)

    # Check if video has audio
    if not _has_audio(video_path):
        logger.info("No audio track found — skipping audio clean")
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    audio_filters = []

    if remove_noise:
        audio_filters.append("afftdn=nr=12:nf=-25:tn=1")

    if enhance_voice:
        audio_filters.append("highpass=f=80")
        audio_filters.append("lowpass=f=13000")
        audio_filters.append("acompressor=threshold=-20dB:ratio=3:attack=5:release=50")
        audio_filters.append("adeclick")

    if normalize_volume:
        audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    if not audio_filters:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    af = ",".join(audio_filters)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "copy",
        "-af", af,
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("Audio clean failed, using original: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)
    else:
        logger.info("Audio cleaned successfully")

    if progress_callback:
        progress_callback("Audio cleaned", 6)

    return output_path


def _has_audio(video_path: str) -> bool:
    """Check if video has an audio stream."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-print_format", "json", video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        return len(data.get("streams", [])) > 0
    except Exception:
        return False


def analyze_audio_quality(video_path: str) -> dict:
    """Analyze audio quality to decide which cleaning steps are needed."""
    try:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-af", "astats=metadata=1:reset=1",
            "-f", "null", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        rms_level = -20.0
        peak_level = -1.0

        for line in result.stderr.split("\n"):
            rms_match = re.search(r"RMS level dB:\s*(-?\d+\.?\d*)", line)
            peak_match = re.search(r"Peak level dB:\s*(-?\d+\.?\d*)", line)
            if rms_match:
                rms_level = float(rms_match.group(1))
            if peak_match:
                peak_level = float(peak_match.group(1))

        return {
            "rms_level_db": rms_level,
            "peak_level_db": peak_level,
            "needs_normalization": rms_level < -24 or rms_level > -12,
            "needs_noise_reduction": True,
            "needs_voice_enhance": rms_level < -20,
        }
    except Exception:
        return {
            "needs_normalization": True,
            "needs_noise_reduction": True,
            "needs_voice_enhance": True,
        }
