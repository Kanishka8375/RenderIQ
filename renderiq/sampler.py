"""Smart frame extraction from reference videos.

Implements uniform sampling and scene change detection to select
strategically chosen keyframes for color analysis.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from renderiq.utils import get_video_info

logger = logging.getLogger(__name__)


def extract_keyframes(
    video_path: str,
    interval_seconds: float = 2.0,
    scene_threshold: float = 0.3,
    max_frames: int = 300,
) -> list[dict]:
    """Extract keyframes using uniform sampling + scene change detection.

    Args:
        video_path: Path to the video file.
        interval_seconds: Seconds between uniform samples.
        scene_threshold: FFmpeg scene detection threshold (0.0-1.0).
        max_frames: Maximum number of frames to return.

    Returns:
        List of dicts with keys: frame (np.ndarray RGB), timestamp (float),
        source ("uniform" | "scene_change").
    """
    info = get_video_info(video_path)
    duration = info["duration"]

    if duration <= 0:
        raise ValueError(f"Video has invalid duration: {duration}")

    # 1.4: Short video handling — use 1fps for videos under 5 seconds
    if duration < 5.0:
        interval_seconds = 1.0

    # Collect timestamps from both strategies
    uniform_ts = _uniform_timestamps(duration, interval_seconds)
    scene_ts = _scene_change_timestamps(video_path, scene_threshold)

    logger.info(
        "Sampling: %d uniform, %d scene-change timestamps",
        len(uniform_ts), len(scene_ts),
    )

    # Merge and deduplicate (within 0.5s proximity)
    merged = _merge_timestamps(uniform_ts, scene_ts, min_gap=0.5)

    # 1.4: Ensure at least 3 keyframes for very short videos
    if len(merged) < 3 and duration > 0:
        extra_ts = np.linspace(0, max(duration - 0.01, 0), 3)
        for t in extra_ts:
            merged.append((float(t), "uniform"))
        merged = _merge_timestamps(merged, [], min_gap=0.1)
        if len(merged) < 3:
            # force at least 3 even if they overlap
            merged = [(float(t), "uniform") for t in extra_ts]

    # Cap total frames
    if len(merged) > max_frames:
        step = len(merged) / max_frames
        merged = [merged[int(i * step)] for i in range(max_frames)]

    # Extract actual frames
    frames = _extract_frames_at_timestamps(video_path, merged)

    # 1.4: Ensure minimum 3 frames returned
    if len(frames) < 3 and duration > 0:
        # Try extracting at different positions
        fallback_ts = [(0.0, "uniform")]
        if duration > 0.1:
            fallback_ts.append((duration / 2, "uniform"))
        if duration > 0.2:
            fallback_ts.append((max(duration - 0.1, 0), "uniform"))
        extra_frames = _extract_frames_at_timestamps(video_path, fallback_ts)
        seen_ts = {f["timestamp"] for f in frames}
        for ef in extra_frames:
            if ef["timestamp"] not in seen_ts and len(frames) < 3:
                frames.append(ef)
                seen_ts.add(ef["timestamp"])
        # If still not enough, duplicate the first frame
        while len(frames) < 3 and frames:
            frames.append(dict(frames[0]))

    logger.info("Extracted %d keyframes", len(frames))
    return frames


def _uniform_timestamps(
    duration: float, interval: float
) -> list[tuple[float, str]]:
    """Generate uniformly spaced timestamps."""
    timestamps = []
    t = 0.0
    while t < duration:
        timestamps.append((t, "uniform"))
        t += interval
    return timestamps


def _scene_change_timestamps(
    video_path: str, threshold: float
) -> list[tuple[float, str]]:
    """Detect scene changes using FFmpeg's scene filter."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-"
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        # Parse showinfo output for pts_time
        timestamps = []
        for line in result.stderr.split("\n"):
            if "pts_time:" in line:
                parts = line.split("pts_time:")
                if len(parts) > 1:
                    time_str = parts[1].strip().split()[0]
                    try:
                        ts = float(time_str)
                        timestamps.append((ts, "scene_change"))
                    except ValueError:
                        continue
        return timestamps
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.warning("Scene detection failed: %s. Falling back to uniform only.", e)
        return []


def _merge_timestamps(
    uniform: list[tuple[float, str]],
    scene: list[tuple[float, str]],
    min_gap: float = 0.5,
) -> list[tuple[float, str]]:
    """Merge timestamp lists, removing near-duplicates within min_gap seconds.

    Scene change timestamps take priority when deduplicating.
    """
    # Combine all timestamps, scene_change entries first for priority
    all_ts = sorted(scene + uniform, key=lambda x: x[0])

    if not all_ts:
        return []

    merged = [all_ts[0]]
    for ts, source in all_ts[1:]:
        prev_ts = merged[-1][0]
        if ts - prev_ts >= min_gap:
            merged.append((ts, source))
        elif source == "scene_change" and merged[-1][1] != "scene_change":
            # Replace uniform with scene_change if they're close
            merged[-1] = (ts, source)

    return merged


def _extract_frames_at_timestamps(
    video_path: str,
    timestamps: list[tuple[float, str]],
) -> list[dict]:
    """Extract frames at specific timestamps using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frames = []
    for ts, source in timestamps:
        frame_idx = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append({
                "frame": frame_rgb,
                "timestamp": ts,
                "source": source,
            })

    cap.release()
    return frames
