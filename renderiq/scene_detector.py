"""
Scene Detection Module (Module 3)
Detect cut boundaries, score scene interest, and extract scene metadata.
Uses FFmpeg scene detection filter + OpenCV analysis.
"""
import subprocess
import json
import logging
import re
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_scenes(
    video_path: str,
    threshold: float = 0.3,
    min_scene_duration: float = 1.0,
    progress_callback=None,
) -> List[dict]:
    """
    Detect scene boundaries in a video.

    Returns list of scenes:
    [
        {
            "start_time": 0.0,
            "end_time": 3.5,
            "duration": 3.5,
            "interest_score": 0.72,
            "motion_score": 0.45,
            "brightness": 0.6,
        },
        ...
    ]
    """
    if progress_callback:
        progress_callback("Detecting scenes...", 15)

    duration = _get_duration(video_path)
    if duration <= 0:
        return [{"start_time": 0, "end_time": 1, "duration": 1,
                 "interest_score": 0.5, "motion_score": 0.5, "brightness": 0.5}]

    # Use FFmpeg scene detection
    cut_points = _detect_cuts_ffmpeg(video_path, threshold)

    # Build scene list from cut points
    scenes = []
    boundaries = [0.0] + sorted(cut_points) + [duration]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        dur = end - start

        if dur < min_scene_duration and scenes:
            # Merge short scenes with previous
            scenes[-1]["end_time"] = end
            scenes[-1]["duration"] = end - scenes[-1]["start_time"]
            continue

        scenes.append({
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": round(dur, 3),
            "interest_score": 0.5,
            "motion_score": 0.5,
            "brightness": 0.5,
        })

    # Score scenes with visual analysis
    scenes = _score_scenes(video_path, scenes)

    logger.info("Detected %d scenes in %.1fs video", len(scenes), duration)

    if progress_callback:
        progress_callback(f"{len(scenes)} scenes detected", 20)

    return scenes


def _detect_cuts_ffmpeg(video_path: str, threshold: float) -> List[float]:
    """Use FFmpeg select filter to find scene changes."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    cuts = []
    for line in result.stderr.split("\n"):
        match = re.search(r"pts_time:(\d+\.?\d*)", line)
        if match:
            t = float(match.group(1))
            if t > 0.5:  # Skip very early detections
                cuts.append(t)

    return cuts


def _score_scenes(video_path: str, scenes: List[dict]) -> List[dict]:
    """Score each scene for interest, motion, and brightness."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    prev_gray = None

    for scene in scenes:
        mid = (scene["start_time"] + scene["end_time"]) / 2
        cap.set(cv2.CAP_PROP_POS_MSEC, mid * 1000)
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Brightness (0-1)
        scene["brightness"] = round(float(np.mean(gray)) / 255.0, 3)

        # Motion score (compare with previous scene frame)
        if prev_gray is not None and prev_gray.shape == gray.shape:
            diff = cv2.absdiff(prev_gray, gray)
            scene["motion_score"] = round(min(1.0, float(np.mean(diff)) / 40.0), 3)
        else:
            scene["motion_score"] = 0.5

        prev_gray = gray

        # Interest score = weighted combo of motion + contrast
        contrast = float(np.std(gray)) / 128.0
        scene["interest_score"] = round(
            min(1.0, 0.4 * scene["motion_score"] + 0.3 * contrast + 0.3 * scene["brightness"]),
            3,
        )

    cap.release()
    return scenes


def _get_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0
