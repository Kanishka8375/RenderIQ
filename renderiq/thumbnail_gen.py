"""
Thumbnail Generator Module (Module 14)
Select the best frame and create a thumbnail with optional text.
"""
import subprocess
import json
import os
import logging
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def generate_thumbnail(
    video_path: str,
    scenes: Optional[List[dict]] = None,
    face_data: Optional[List[dict]] = None,
    title_text: Optional[str] = None,
    output_path: str = None,
    resolution: tuple = (1280, 720),
    progress_callback=None,
) -> str:
    """
    Generate a thumbnail from the best frame in the video.

    Best frame selection criteria:
    1. Has a face (priority)
    2. High brightness (not too dark)
    3. High interest score (from scene detection)
    4. Good contrast
    """
    if progress_callback:
        progress_callback("Generating thumbnail...", 92)

    best_timestamp = _find_best_frame(video_path, scenes, face_data)

    frame_path = output_path or os.path.join(os.path.dirname(video_path), "thumbnail.jpg")

    vf = (
        f"scale={resolution[0]}:{resolution[1]}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={resolution[0]}:{resolution[1]}:-1:-1:color=black"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(best_timestamp),
        "-i", video_path,
        "-frames:v", "1",
        "-vf", vf,
        "-q:v", "2",
        frame_path,
    ]

    subprocess.run(cmd, capture_output=True, timeout=15)

    if title_text and os.path.exists(frame_path):
        _add_thumbnail_text(frame_path, title_text, frame_path)

    if os.path.exists(frame_path):
        _enhance_thumbnail(frame_path)

    logger.info("Thumbnail generated at t=%.1fs -> %s", best_timestamp, frame_path)

    if progress_callback:
        progress_callback("Thumbnail ready", 94)

    return frame_path


def _find_best_frame(video_path, scenes, face_data) -> float:
    """Find the timestamp of the best thumbnail frame."""
    candidates = []

    if scenes:
        for scene in sorted(
            scenes, key=lambda s: s.get("interest_score", 0), reverse=True
        )[:5]:
            mid = (scene["start_time"] + scene["end_time"]) / 2
            score = scene.get("interest_score", 0.5)

            has_face = False
            if face_data:
                has_face = any(
                    f["has_face"]
                    for f in face_data
                    if scene["start_time"] <= f["timestamp"] <= scene["end_time"]
                )

            if has_face:
                score += 0.3

            candidates.append((mid, score))

    if not candidates:
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", video_path,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            duration = float(json.loads(r.stdout)["format"]["duration"])
        except Exception:
            duration = 60.0

        for pct in [0.1, 0.25, 0.5, 0.75]:
            candidates.append((duration * pct, 0.5))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0] if candidates else 5.0


def _add_thumbnail_text(image_path: str, text: str, output_path: str):
    """Add bold text to thumbnail image."""
    try:
        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        overlay = img.copy()
        cv2.rectangle(overlay, (0, h - 120), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 1.5
        thickness = 3

        (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
        x = (w - text_w) // 2
        y = h - 50

        cv2.putText(img, text, (x + 2, y + 2), font, font_scale, (0, 0, 0), thickness + 2)
        cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness)

        cv2.imwrite(output_path, img)
    except Exception as e:
        logger.warning("Thumbnail text overlay failed: %s", e)


def _enhance_thumbnail(image_path: str):
    """Slightly boost saturation and contrast for a punchier thumbnail."""
    try:
        img = cv2.imread(image_path)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= 1.2
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        cv2.imwrite(image_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    except Exception as e:
        logger.warning("Thumbnail enhancement failed: %s", e)
