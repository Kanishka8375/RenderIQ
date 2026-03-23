"""Enhanced visual scene analysis — goes beyond color histograms."""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def analyze_visual_content(keyframes: list[dict]) -> dict:
    """Analyze visual characteristics of keyframes for mood detection.

    Returns dict with scene_type, brightness, saturation, contrast,
    warmth, dominant_hue, color_variety, has_faces, motion_level,
    and visual_tags.
    """
    if not keyframes:
        raise ValueError("No keyframes provided")

    frames = [kf["frame"] for kf in keyframes]

    # Brightness (LAB L channel, normalized 0-1)
    brightness_values = []
    for frame in frames:
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
        brightness_values.append(np.mean(lab[:, :, 0]) / 255.0)
    brightness = float(np.mean(brightness_values))

    # Saturation (HSV S channel, normalized 0-1)
    saturation_values = []
    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        saturation_values.append(np.mean(hsv[:, :, 1]) / 255.0)
    saturation_level = float(np.mean(saturation_values))

    # Contrast (std of luminance, normalized)
    contrast_values = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        contrast_values.append(np.std(gray) / 128.0)
    contrast_level = float(np.clip(np.mean(contrast_values), 0, 1))

    # Warmth (ratio of warm to cool hue pixels)
    warm_ratios = []
    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0]
        warm_pixels = np.sum((hue < 30) | (hue > 150))
        cool_pixels = np.sum((hue > 75) & (hue < 130))
        warm_ratio = warm_pixels / max(warm_pixels + cool_pixels, 1)
        warm_ratios.append(warm_ratio)
    warmth = float(np.mean(warm_ratios))

    # Dominant hue
    all_hues = []
    for frame in frames:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        mask = hsv[:, :, 1] > 50
        if np.any(mask):
            all_hues.extend(hsv[:, :, 0][mask].flatten().tolist())

    if all_hues:
        hue_hist, _ = np.histogram(all_hues, bins=12, range=(0, 180))
        dominant_hue_idx = int(np.argmax(hue_hist))
        hue_names = [
            "red", "orange", "yellow", "yellow-green", "green", "cyan",
            "light-blue", "blue", "purple", "magenta", "pink", "red",
        ]
        dominant_hue = hue_names[dominant_hue_idx]
        color_variety = float(np.count_nonzero(hue_hist > hue_hist.max() * 0.2) / 12.0)
    else:
        dominant_hue = "neutral"
        color_variety = 0.0

    # Face detection (Haar cascade — lightweight)
    has_faces = False
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        for frame in frames[:10]:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) > 0:
                has_faces = True
                break
    except Exception:
        logger.debug("Face detection unavailable, skipping")

    # Motion estimation (frame-to-frame difference)
    motion_values = []
    for i in range(1, min(len(frames), 20)):
        diff = cv2.absdiff(
            cv2.cvtColor(frames[i], cv2.COLOR_RGB2GRAY),
            cv2.cvtColor(frames[i - 1], cv2.COLOR_RGB2GRAY),
        )
        motion_values.append(np.mean(diff) / 255.0)
    motion_level = float(np.mean(motion_values)) if motion_values else 0.0
    motion_level = float(np.clip(motion_level * 5, 0, 1))

    # Generate visual tags
    visual_tags = []
    if brightness > 0.6:
        visual_tags.append("bright")
    elif brightness < 0.3:
        visual_tags.append("dark")
    if saturation_level > 0.5:
        visual_tags.append("colorful")
    elif saturation_level < 0.2:
        visual_tags.append("muted")
    if warmth > 0.6:
        visual_tags.append("warm")
    elif warmth < 0.35:
        visual_tags.append("cool")
    if has_faces:
        visual_tags.append("people")
    if motion_level > 0.5:
        visual_tags.append("action")
    elif motion_level < 0.15:
        visual_tags.append("static")
    if contrast_level > 0.6:
        visual_tags.append("high-contrast")
    elif contrast_level < 0.3:
        visual_tags.append("flat")

    scene_type = _classify_scene(
        brightness, saturation_level, warmth, has_faces, motion_level, dominant_hue,
    )
    visual_tags.append(scene_type)

    return {
        "scene_type": scene_type,
        "brightness": brightness,
        "saturation_level": saturation_level,
        "contrast_level": contrast_level,
        "warmth": warmth,
        "dominant_hue": dominant_hue,
        "color_variety": color_variety,
        "has_faces": has_faces,
        "motion_level": motion_level,
        "visual_tags": visual_tags,
    }


def _classify_scene(brightness, saturation, warmth, has_faces, motion, dominant_hue):
    """Classify scene into a descriptive category."""
    if brightness < 0.25:
        return "night" if saturation > 0.3 else "low_light"
    if has_faces and motion < 0.3:
        return "portrait"
    if motion > 0.6:
        return "action"
    if saturation > 0.5 and dominant_hue in ("green", "yellow-green", "cyan"):
        return "nature"
    if brightness > 0.65 and warmth > 0.5:
        return "outdoor_warm"
    if brightness > 0.5 and warmth < 0.4:
        return "outdoor_cool"
    if warmth > 0.55:
        return "indoor_warm"
    return "general"
