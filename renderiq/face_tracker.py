"""
Face Tracking Module (Module 8)
Detect and track faces across video frames.
Used by Auto Zoom and Reframe modules.
"""
import os
import logging
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def track_faces(
    video_path: str,
    sample_interval: float = 0.5,
    max_frames: int = 200,
    progress_callback=None,
) -> List[dict]:
    """
    Detect faces at regular intervals throughout the video.

    Returns list of face detections per timestamp:
    [
        {
            "timestamp": 0.0,
            "faces": [{"x": 100, "y": 50, "w": 200, "h": 200, "confidence": 0.95}],
            "primary_face": {"cx": 200, "cy": 150, "w": 200, "h": 200},
            "has_face": True
        },
        ...
    ]
    """
    if progress_callback:
        progress_callback("Tracking faces...", 22)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    # Load face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    dnn_detector = _load_dnn_detector()

    detections = []
    frame_count = 0
    current_time = 0.0

    while current_time < duration and frame_count < max_frames:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()

        if not ret:
            break

        faces = _detect_faces(frame, face_cascade, dnn_detector)

        primary = None
        if faces:
            largest = max(faces, key=lambda f: f["w"] * f["h"])
            primary = {
                "cx": largest["x"] + largest["w"] // 2,
                "cy": largest["y"] + largest["h"] // 2,
                "w": largest["w"],
                "h": largest["h"],
            }

        detections.append({
            "timestamp": round(current_time, 3),
            "faces": faces,
            "primary_face": primary,
            "has_face": len(faces) > 0,
        })

        current_time += sample_interval
        frame_count += 1

    cap.release()

    detections = _smooth_face_positions(detections)

    face_count = sum(1 for d in detections if d["has_face"])
    logger.info("Face tracking: %d/%d frames have faces", face_count, len(detections))

    if progress_callback:
        progress_callback(f"Tracked {face_count} face frames", 24)

    return detections


def _detect_faces(frame, cascade, dnn_detector=None) -> list:
    """Detect faces in a single frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = frame.shape[:2]

    # Try DNN first (more accurate)
    if dnn_detector is not None:
        try:
            blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123])
            dnn_detector.setInput(blob)
            detections = dnn_detector.forward()

            faces = []
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.5:
                    box = detections[0, 0, i, 3:7] * [w, h, w, h]
                    x, y, x2, y2 = box.astype(int)
                    faces.append({
                        "x": max(0, x),
                        "y": max(0, y),
                        "w": min(x2 - x, w - x),
                        "h": min(y2 - y, h - y),
                        "confidence": float(confidence),
                    })

            if faces:
                return faces
        except Exception:
            pass

    # Fallback: Haar cascade
    face_rects = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(int(w * 0.05), int(h * 0.05)),
    )

    return [
        {"x": int(x), "y": int(y), "w": int(fw), "h": int(fh), "confidence": 0.7}
        for (x, y, fw, fh) in face_rects
    ]


def _load_dnn_detector():
    """Try to load OpenCV DNN face detector."""
    try:
        base = cv2.data.haarcascades
        model_path = os.path.join(base, "..", "res10_300x300_ssd_iter_140000.caffemodel")
        config_path = os.path.join(base, "..", "deploy.prototxt")

        if os.path.exists(model_path) and os.path.exists(config_path):
            return cv2.dnn.readNetFromCaffe(config_path, model_path)
    except Exception:
        pass
    return None


def _smooth_face_positions(detections: list, window: int = 5) -> list:
    """Smooth face positions across frames to reduce jitter."""
    if len(detections) < window:
        return detections

    positions = []
    for d in detections:
        if d["primary_face"]:
            positions.append((d["primary_face"]["cx"], d["primary_face"]["cy"]))
        else:
            positions.append(None)

    smoothed = list(positions)
    half_w = window // 2

    for i in range(len(positions)):
        if positions[i] is None:
            continue

        nearby = []
        for j in range(max(0, i - half_w), min(len(positions), i + half_w + 1)):
            if positions[j] is not None:
                nearby.append(positions[j])

        if nearby:
            avg_cx = int(np.mean([p[0] for p in nearby]))
            avg_cy = int(np.mean([p[1] for p in nearby]))
            smoothed[i] = (avg_cx, avg_cy)

    for i, d in enumerate(detections):
        if d["primary_face"] and smoothed[i]:
            d["primary_face"]["cx"] = smoothed[i][0]
            d["primary_face"]["cy"] = smoothed[i][1]

    return detections
