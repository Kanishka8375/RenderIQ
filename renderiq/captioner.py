"""
Auto Captions Module (Module 6)
Speech-to-text transcription and styled subtitle burning.
Uses FFmpeg for audio extraction and subtitle rendering.
"""
import subprocess
import os
import json
import logging
import re
import tempfile
from typing import List

logger = logging.getLogger(__name__)

CAPTION_STYLES = {
    "bold": {
        "fontsize": 24,
        "fontcolor": "white",
        "borderw": 3,
        "bordcolor": "black",
        "font": "DejaVuSans-Bold",
    },
    "minimal": {
        "fontsize": 20,
        "fontcolor": "white@0.9",
        "borderw": 1,
        "bordcolor": "black@0.5",
        "font": "DejaVuSans",
    },
    "viral": {
        "fontsize": 28,
        "fontcolor": "yellow",
        "borderw": 4,
        "bordcolor": "black",
        "font": "DejaVuSans-Bold",
    },
}


def generate_subtitles(
    video_path: str,
    output_srt: str,
    progress_callback=None,
) -> str:
    """
    Generate SRT subtitles from video audio.

    Uses Whisper if available, otherwise falls back to
    silence-based segmentation with placeholder text.
    """
    if progress_callback:
        progress_callback("Generating captions...", 70)

    # Try whisper first
    try:
        return _generate_with_whisper(video_path, output_srt)
    except Exception as e:
        logger.info("Whisper not available (%s), using silence-based segmentation", e)

    # Fallback: silence-based SRT with timing markers
    return _generate_silence_based(video_path, output_srt)


def _generate_with_whisper(video_path: str, output_srt: str) -> str:
    """Use OpenAI Whisper for speech-to-text."""
    import whisper  # noqa: F811 — optional dependency

    # Extract audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-f", "wav",
            tmp_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)

        model = whisper.load_model("base")
        result = model.transcribe(tmp_path, task="transcribe")

        # Write SRT
        with open(output_srt, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result.get("segments", []), 1):
                start = _format_srt_time(seg["start"])
                end = _format_srt_time(seg["end"])
                text = seg["text"].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

        return output_srt
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _generate_silence_based(video_path: str, output_srt: str) -> str:
    """
    Fallback: detect speech segments via silence detection.
    Creates SRT with timing but no text content (placeholder markers).
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Parse silence boundaries
    silence_starts = []
    silence_ends = []
    for line in result.stderr.split("\n"):
        start_match = re.search(r"silence_start:\s*(\d+\.?\d*)", line)
        end_match = re.search(r"silence_end:\s*(\d+\.?\d*)", line)
        if start_match:
            silence_starts.append(float(start_match.group(1)))
        if end_match:
            silence_ends.append(float(end_match.group(1)))

    duration = _get_duration(video_path)

    # Build speech segments (inverse of silence)
    speech_segments = []
    prev_end = 0.0

    for s_start in silence_starts:
        if s_start - prev_end > 0.5:
            speech_segments.append((prev_end, s_start))
        prev_end = s_start

    if silence_ends:
        last_silence_end = silence_ends[-1] if silence_ends else 0
        if duration - last_silence_end > 0.5:
            speech_segments.append((last_silence_end, duration))
    elif not speech_segments:
        # No silence detected — create uniform segments
        seg_duration = 4.0
        t = 0.0
        while t < duration:
            speech_segments.append((t, min(t + seg_duration, duration)))
            t += seg_duration

    # Write SRT with placeholder text
    with open(output_srt, "w", encoding="utf-8") as f:
        for i, (start, end) in enumerate(speech_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            f.write(f"[Speech segment {i}]\n\n")

    logger.info("Generated %d caption segments (silence-based)", len(speech_segments))
    return output_srt


def burn_captions(
    video_path: str,
    srt_path: str,
    output_path: str,
    style: str = "bold",
    progress_callback=None,
) -> str:
    """Burn SRT subtitles into video using FFmpeg."""
    if progress_callback:
        progress_callback("Burning captions...", 75)

    if not os.path.exists(srt_path):
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    s = CAPTION_STYLES.get(style, CAPTION_STYLES["bold"])

    # Escape the SRT path for FFmpeg subtitles filter
    escaped_srt = srt_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")

    vf = (
        f"subtitles='{escaped_srt}'"
        f":force_style='Fontname={s['font']},Fontsize={s['fontsize']},"
        f"PrimaryColour=&Hffffff&,OutlineColour=&H000000&,"
        f"Outline={s['borderw']},Shadow=1,MarginV=30'"
    )

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("Caption burn failed: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)

    if progress_callback:
        progress_callback("Captions applied", 78)

    return output_path


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _get_duration(video_path: str) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 60.0
