"""
Music Sync Module (Module 5)
Detect beats in audio and align scene cuts to beat positions.
Uses FFmpeg audio analysis.
"""
import subprocess
import json
import logging
import os
import re
import tempfile
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


def detect_beats(
    video_path: str,
    progress_callback=None,
) -> List[float]:
    """
    Detect beat/onset positions in the audio track.

    Returns list of beat timestamps in seconds.
    Uses FFmpeg's ebur128 + onset energy analysis.
    """
    if progress_callback:
        progress_callback("Analyzing audio beats...", 35)

    # Check for audio stream
    if not _has_audio(video_path):
        logger.info("No audio stream — skipping beat detection")
        return []

    # Extract audio and analyze energy onsets
    beats = _detect_onsets_via_energy(video_path)

    logger.info("Detected %d beats/onsets", len(beats))

    if progress_callback:
        progress_callback(f"Found {len(beats)} beats", 38)

    return beats


def _detect_onsets_via_energy(video_path: str) -> List[float]:
    """Detect audio energy onsets using FFmpeg's astats filter."""
    # Extract raw audio samples and compute energy
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "22050", "-f", "wav",
            tmp_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)

        if not os.path.exists(tmp_path):
            return []

        # Use FFmpeg to get volume levels
        cmd = [
            "ffmpeg", "-i", tmp_path,
            "-af", "astats=metadata=1:reset=0.1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
            "-f", "null", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Parse energy levels and find peaks
        times = []
        levels = []
        for line in result.stderr.split("\n"):
            time_match = re.search(r"pts_time:(\d+\.?\d*)", line)
            level_match = re.search(r"RMS_level=(-?\d+\.?\d*)", line)
            if time_match:
                times.append(float(time_match.group(1)))
            if level_match:
                levels.append(float(level_match.group(1)))

        if not levels:
            return _fallback_uniform_beats(video_path)

        # Find energy peaks (beats)
        levels_arr = np.array(levels[:len(times)])
        if len(levels_arr) < 3:
            return _fallback_uniform_beats(video_path)

        mean_level = np.mean(levels_arr)
        std_level = np.std(levels_arr)
        threshold = mean_level + 0.5 * std_level

        beats = []
        min_gap = 0.3  # Minimum gap between beats
        for i, (t, level) in enumerate(zip(times, levels_arr)):
            if level > threshold:
                if not beats or (t - beats[-1]) >= min_gap:
                    beats.append(round(t, 3))

        return beats[:200]  # Cap at 200 beats

    except Exception as e:
        logger.warning("Beat detection failed: %s", e)
        return _fallback_uniform_beats(video_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _fallback_uniform_beats(video_path: str, bpm: float = 120.0) -> List[float]:
    """Generate uniform beats at assumed BPM when detection fails."""
    duration = _get_duration(video_path)
    interval = 60.0 / bpm
    return [round(i * interval, 3) for i in range(int(duration / interval))]


def sync_cuts_to_beats(
    scenes: List[dict],
    beats: List[float],
    max_shift: float = 0.5,
) -> List[dict]:
    """
    Shift scene cut points to align with nearest beats.

    Only shifts cuts within max_shift seconds of a beat.
    """
    if not beats or not scenes:
        return scenes

    synced = []
    for scene in scenes:
        s = dict(scene)
        # Find nearest beat to scene start
        nearest = min(beats, key=lambda b: abs(b - s["start_time"]))
        shift = nearest - s["start_time"]

        if abs(shift) <= max_shift:
            s["start_time"] = round(nearest, 3)
            s["duration"] = round(s["end_time"] - s["start_time"], 3)
            if s["duration"] <= 0:
                s["duration"] = 0.1

        synced.append(s)

    return synced


def _has_audio(video_path: str) -> bool:
    """Check if video has audio stream."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-print_format", "json", video_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout)
        return len(data.get("streams", [])) > 0
    except Exception:
        return False


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
