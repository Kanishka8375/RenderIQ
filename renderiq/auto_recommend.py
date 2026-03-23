"""Automatic preset recommendation based on video content analysis.

Analyzes the uploaded footage's visual characteristics (brightness,
saturation, color temperature, contrast, scene type) and scores each
preset for suitability. Returns a ranked list of recommendations with
explanations.
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Preset suitability rules — each preset has ideal conditions and
# content affinities. Scores are computed by how well the footage
# matches these conditions.
PRESET_RULES = {
    "cinematic_warm": {
        "ideal_brightness": (80, 170),   # works on mid-range footage
        "ideal_saturation": (40, 160),
        "prefers_warm": False,           # best applied to neutral/cool footage
        "prefers_cool": True,
        "contrast_boost": "moderate",
        "best_for": ["outdoor", "portrait", "narrative", "warm_light"],
        "avoid": ["already_warm", "very_dark"],
        "description": "Adds warm amber tones for cinematic drama",
    },
    "cinematic_cold": {
        "ideal_brightness": (70, 170),
        "ideal_saturation": (30, 150),
        "prefers_warm": True,            # cool grade on warm footage = balanced
        "prefers_cool": False,
        "contrast_boost": "moderate",
        "best_for": ["indoor", "urban", "night", "tech", "cool_light"],
        "avoid": ["already_cool", "very_dark"],
        "description": "Adds cool teal tones for a modern cinematic feel",
    },
    "teal_orange": {
        "ideal_brightness": (90, 180),
        "ideal_saturation": (50, 170),
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "moderate",
        "best_for": ["outdoor", "portrait", "action", "travel"],
        "avoid": ["very_dark", "low_sat"],
        "description": "Classic blockbuster look with complementary teal/orange split",
    },
    "vintage_film": {
        "ideal_brightness": (80, 190),
        "ideal_saturation": (40, 140),
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "low",
        "best_for": ["outdoor", "travel", "casual", "daylight", "retro"],
        "avoid": ["very_dark", "high_contrast"],
        "description": "Faded nostalgic look with lifted blacks and soft warmth",
    },
    "high_contrast_bw": {
        "ideal_brightness": (60, 200),
        "ideal_saturation": (0, 255),    # works on anything
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "high",
        "best_for": ["portrait", "architecture", "street", "high_contrast", "dramatic"],
        "avoid": ["low_contrast"],
        "description": "Dramatic black and white — great for texture and emotion",
    },
    "moody_dark": {
        "ideal_brightness": (60, 150),   # works better on already-dim footage
        "ideal_saturation": (30, 130),
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "high",
        "best_for": ["indoor", "night", "urban", "dramatic", "dark"],
        "avoid": ["bright", "outdoor_sunny"],
        "description": "Dark and brooding with crushed shadows and muted color",
    },
    "pastel_soft": {
        "ideal_brightness": (100, 220),
        "ideal_saturation": (50, 170),
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "low",
        "best_for": ["outdoor", "portrait", "lifestyle", "bright", "daylight"],
        "avoid": ["very_dark", "night"],
        "description": "Light and dreamy with soft lifted tones",
    },
    "neon_night": {
        "ideal_brightness": (30, 130),
        "ideal_saturation": (40, 200),
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "moderate",
        "best_for": ["night", "urban", "neon", "indoor_dark", "party"],
        "avoid": ["bright", "outdoor_sunny", "daylight"],
        "description": "Vibrant night look with boosted blues and magentas",
    },
    "golden_hour": {
        "ideal_brightness": (90, 190),
        "ideal_saturation": (40, 170),
        "prefers_warm": False,
        "prefers_cool": True,
        "contrast_boost": "low",
        "best_for": ["outdoor", "portrait", "landscape", "daylight", "sunset"],
        "avoid": ["already_warm", "night", "indoor_dark"],
        "description": "Warm golden tones replicating sunset magic",
    },
    "anime_vibrant": {
        "ideal_brightness": (80, 200),
        "ideal_saturation": (30, 140),   # best on unsaturated footage (room to boost)
        "prefers_warm": False,
        "prefers_cool": False,
        "contrast_boost": "high",
        "best_for": ["outdoor", "action", "colorful", "travel"],
        "avoid": ["already_saturated", "very_dark"],
        "description": "Ultra-vivid with boosted saturation and strong contrast",
    },
}


def analyze_video_characteristics(keyframes: list[dict]) -> dict:
    """Analyze video content characteristics for preset recommendation.

    Args:
        keyframes: List of dicts with "frame" key containing RGB np.ndarray.

    Returns:
        Dict with brightness, saturation, color_temp, contrast, and
        scene classification tags.
    """
    if not keyframes:
        raise ValueError("No keyframes provided")

    frames = [kf["frame"] for kf in keyframes]

    # Aggregate stats across all frames
    l_values = []
    sat_values = []
    a_values = []  # color temperature proxy
    b_values = []
    contrast_values = []

    for frame in frames:
        lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        l_values.append(lab[:, :, 0].mean())
        a_values.append(lab[:, :, 1].mean())
        b_values.append(lab[:, :, 2].mean())
        sat_values.append(hsv[:, :, 1].mean())
        contrast_values.append(lab[:, :, 0].std())

    avg_brightness = float(np.mean(l_values))     # 0-255 (uint8 LAB L)
    avg_saturation = float(np.mean(sat_values))    # 0-255 (HSV S)
    avg_a = float(np.mean(a_values))               # 128 = neutral
    avg_b = float(np.mean(b_values))               # 128 = neutral
    avg_contrast = float(np.mean(contrast_values))

    # Color temperature: b > 128 = warm, b < 128 = cool
    # Also a > 128 = reddish, a < 128 = greenish
    color_temp = "neutral"
    if avg_b > 138:
        color_temp = "warm"
    elif avg_b < 118:
        color_temp = "cool"

    # Scene classification tags
    tags = []

    if avg_brightness > 160:
        tags.append("bright")
        tags.append("daylight")
    elif avg_brightness > 120:
        tags.append("daylight")
    elif avg_brightness > 80:
        tags.append("indoor")
    else:
        tags.append("dark")
        tags.append("night")

    if avg_brightness < 60:
        tags.append("very_dark")
        tags.append("indoor_dark")

    if avg_saturation > 120:
        tags.append("colorful")
        tags.append("already_saturated")
    elif avg_saturation < 50:
        tags.append("low_sat")

    if color_temp == "warm":
        tags.append("warm_light")
        tags.append("already_warm")
    elif color_temp == "cool":
        tags.append("cool_light")
        tags.append("already_cool")

    if avg_contrast > 55:
        tags.append("high_contrast")
    elif avg_contrast < 30:
        tags.append("low_contrast")

    # Outdoor vs indoor heuristic: bright + moderate-high saturation = likely outdoor
    if avg_brightness > 110 and avg_saturation > 60:
        tags.append("outdoor")
    elif avg_brightness < 100:
        tags.append("indoor")

    if avg_brightness > 140 and avg_b > 135:
        tags.append("outdoor_sunny")

    # Portrait heuristic: moderate brightness + moderate saturation with warm tones
    if 90 < avg_brightness < 180 and avg_a > 125:
        tags.append("portrait")

    return {
        "brightness": avg_brightness,
        "saturation": avg_saturation,
        "color_temp": color_temp,
        "color_a": avg_a,
        "color_b": avg_b,
        "contrast": avg_contrast,
        "tags": list(set(tags)),
    }


def recommend_presets(characteristics: dict, top_n: int = 3) -> list[dict]:
    """Score and rank presets based on video characteristics.

    Args:
        characteristics: Output of analyze_video_characteristics().
        top_n: Number of top recommendations to return.

    Returns:
        List of dicts with preset name, score, and reason.
    """
    brightness = characteristics["brightness"]
    saturation = characteristics["saturation"]
    contrast = characteristics["contrast"]
    color_temp = characteristics["color_temp"]
    tags = set(characteristics["tags"])

    scores = []

    for name, rules in PRESET_RULES.items():
        score = 50.0  # base score

        # 1. Brightness fit (0-20 points)
        bmin, bmax = rules["ideal_brightness"]
        if bmin <= brightness <= bmax:
            # How centered within the ideal range
            mid = (bmin + bmax) / 2
            dist = abs(brightness - mid) / ((bmax - bmin) / 2)
            score += 20 * (1 - dist * 0.5)
        else:
            # Penalty for being outside ideal range
            overshoot = max(bmin - brightness, brightness - bmax, 0)
            score -= min(overshoot * 0.3, 20)

        # 2. Saturation fit (0-15 points)
        smin, smax = rules["ideal_saturation"]
        if smin <= saturation <= smax:
            score += 15
        else:
            overshoot = max(smin - saturation, saturation - smax, 0)
            score -= min(overshoot * 0.2, 15)

        # 3. Color temperature complementarity (0-15 points)
        if rules["prefers_cool"] and color_temp == "cool":
            score += 12
        elif rules["prefers_cool"] and color_temp == "neutral":
            score += 8
        elif rules["prefers_warm"] and color_temp == "warm":
            score += 12
        elif rules["prefers_warm"] and color_temp == "neutral":
            score += 8
        elif not rules["prefers_warm"] and not rules["prefers_cool"]:
            score += 10  # neutral presets work on anything

        # 4. Scene tag affinity (0-20 points)
        best_for = set(rules["best_for"])
        matches = tags & best_for
        if matches:
            score += min(len(matches) * 7, 20)

        # 5. Avoidance penalty (-25 points max)
        avoid = set(rules["avoid"])
        conflicts = tags & avoid
        if conflicts:
            score -= len(conflicts) * 12

        # 6. Contrast consideration (0-10 points)
        cb = rules["contrast_boost"]
        if cb == "high" and contrast < 40:
            score += 10  # low-contrast footage benefits from high-contrast grade
        elif cb == "low" and contrast > 50:
            score += 8   # high-contrast footage benefits from softening
        elif cb == "moderate":
            score += 5   # moderate is safe for most footage

        score = max(score, 0)

        # Build explanation
        reasons = []
        if matches:
            reasons.append(f"fits your {'/'.join(sorted(matches))} footage")
        if rules["prefers_cool"] and color_temp in ("cool", "neutral"):
            reasons.append("complements your lighting with warm tones")
        elif rules["prefers_warm"] and color_temp in ("warm", "neutral"):
            reasons.append("balances your warm footage with cool tones")
        if cb == "high" and contrast < 40:
            reasons.append("adds contrast your footage needs")
        if cb == "low" and contrast > 50:
            reasons.append("softens your high-contrast footage")

        if not reasons:
            reasons.append(rules["description"])

        scores.append({
            "name": name,
            "score": round(score, 1),
            "reason": reasons[0] if reasons else rules["description"],
        })

    # Sort by score descending
    scores.sort(key=lambda x: x["score"], reverse=True)

    return scores[:top_n]
