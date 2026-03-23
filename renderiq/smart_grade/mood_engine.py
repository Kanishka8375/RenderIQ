"""Mood engine — combine audio + visual analysis into a unified mood profile."""

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Shadow/highlight color palettes per mood (normalized RGB)
_SHADOW_HIGHLIGHT_MAP = {
    "epic":        {"shadow": [0.08, 0.05, 0.12], "highlight": [1.0, 0.85, 0.6]},
    "intense":     {"shadow": [0.05, 0.08, 0.12], "highlight": [0.8, 0.85, 0.95]},
    "upbeat":      {"shadow": [0.1, 0.07, 0.05],  "highlight": [1.0, 0.9, 0.7]},
    "dark":        {"shadow": [0.03, 0.05, 0.08], "highlight": [0.6, 0.65, 0.75]},
    "warm":        {"shadow": [0.1, 0.06, 0.04],  "highlight": [1.0, 0.88, 0.65]},
    "melancholic": {"shadow": [0.05, 0.06, 0.1],  "highlight": [0.75, 0.78, 0.85]},
    "calm":        {"shadow": [0.06, 0.06, 0.06], "highlight": [0.95, 0.93, 0.9]},
    "neutral":     {"shadow": [0.05, 0.05, 0.05], "highlight": [0.95, 0.95, 0.95]},
}

# Mood → (preset, base_strength) mapping
_MOOD_PRESET_MAP = {
    ("epic", True, True):          ("cinematic_warm", 0.75),
    ("epic", False, True):         ("teal_orange", 0.7),
    ("epic", True, False):         ("cinematic_warm", 0.6),
    ("epic", False, False):        ("teal_orange", 0.55),
    ("intense", True, True):       ("cinematic_warm", 0.8),
    ("intense", False, True):      ("moody_dark", 0.7),
    ("intense", True, False):      ("cinematic_warm", 0.6),
    ("intense", False, False):     ("cinematic_cold", 0.65),
    ("upbeat", True, True):        ("golden_hour", 0.7),
    ("upbeat", False, True):       ("teal_orange", 0.65),
    ("upbeat", True, False):       ("golden_hour", 0.6),
    ("upbeat", False, False):      ("cinematic_warm", 0.5),
    ("dark", True, True):          ("moody_dark", 0.7),
    ("dark", False, True):         ("cinematic_cold", 0.75),
    ("dark", True, False):         ("vintage_film", 0.6),
    ("dark", False, False):        ("moody_dark", 0.6),
    ("warm", True, True):          ("golden_hour", 0.65),
    ("warm", False, True):         ("cinematic_warm", 0.6),
    ("warm", True, False):         ("golden_hour", 0.55),
    ("warm", False, False):        ("cinematic_warm", 0.45),
    ("melancholic", True, True):   ("vintage_film", 0.65),
    ("melancholic", False, True):  ("cinematic_cold", 0.6),
    ("melancholic", True, False):  ("vintage_film", 0.6),
    ("melancholic", False, False): ("cinematic_cold", 0.5),
    ("calm", True, True):          ("pastel_soft", 0.55),
    ("calm", False, True):         ("cinematic_cold", 0.45),
    ("calm", True, False):         ("pastel_soft", 0.5),
    ("calm", False, False):        ("cinematic_cold", 0.35),
    ("neutral", True, True):       ("cinematic_warm", 0.45),
    ("neutral", False, True):      ("cinematic_cold", 0.4),
    ("neutral", True, False):      ("cinematic_warm", 0.4),
    ("neutral", False, False):     ("cinematic_cold", 0.35),
}

_GRADE_DESCRIPTIONS = {
    "cinematic_warm": "{intensity}, {warmth_w} cinematic grade with golden highlights and rich shadows",
    "cinematic_cold": "{intensity}, {warmth_w} cinematic look with steel blue tones and clean contrast",
    "teal_orange": "Blockbuster teal and orange grade — {intensity} contrast with complementary color split",
    "moody_dark": "Dark, atmospheric grade with crushed shadows and {warmth_w} undertones",
    "golden_hour": "Warm golden tones reminiscent of sunset light — {intensity} and inviting",
    "vintage_film": "Classic film look with faded blacks and {warmth_w} color shift",
    "pastel_soft": "Soft, dreamy grade with lifted shadows and gentle {warmth_w} tones",
    "neon_night": "Vibrant night-time look with boosted neon colors and deep shadows",
    "anime_vibrant": "Bold, vivid colors with strong contrast — anime-inspired {intensity} grade",
    "high_contrast_bw": "Striking black and white with {intensity} contrast",
}


def compute_mood_profile(audio_mood: dict, visual_analysis: dict) -> dict:
    """Combine audio and visual analysis into a unified mood profile.

    Audio weight: 60%, Visual weight: 40%.

    Returns dict with mood label, target grading parameters, recommended
    preset/strength, shadow/highlight colors, description, and confidence.
    """
    # Audio dimensions (60% weight)
    audio_intensity = audio_mood.get("intensity", 0.5)
    audio_warmth = audio_mood.get("warmth", 0.5)
    primary_mood = audio_mood.get("primary_mood", "neutral")

    # Visual dimensions (40% weight)
    vis_brightness = visual_analysis.get("brightness", 0.5)
    vis_saturation = visual_analysis.get("saturation_level", 0.5)
    vis_contrast = visual_analysis.get("contrast_level", 0.5)
    vis_warmth = visual_analysis.get("warmth", 0.5)
    vis_motion = visual_analysis.get("motion_level", 0.3)
    has_faces = visual_analysis.get("has_faces", False)

    # Blend
    blended_warmth = audio_warmth * 0.6 + vis_warmth * 0.4
    blended_intensity = audio_intensity * 0.6 + (vis_contrast * 0.5 + vis_motion * 0.5) * 0.4

    # Target brightness: intense → darker, calm → brighter
    target_brightness = float(np.clip(0.55 - (blended_intensity - 0.5) * 0.3, 0.3, 0.7))

    # Target saturation by mood
    if primary_mood in ("epic", "upbeat"):
        target_saturation = float(np.clip(0.6 + blended_intensity * 0.3, 0.5, 0.9))
    elif primary_mood in ("melancholic", "calm"):
        target_saturation = float(np.clip(0.3 + blended_warmth * 0.2, 0.2, 0.5))
    elif primary_mood in ("dark", "intense"):
        target_saturation = float(np.clip(0.4 + blended_intensity * 0.2, 0.3, 0.7))
    else:
        target_saturation = 0.5

    # Target contrast: intense → higher
    target_contrast = float(np.clip(0.4 + blended_intensity * 0.5, 0.3, 0.9))

    # Shadow/highlight colors
    colors = _SHADOW_HIGHLIGHT_MAP.get(primary_mood, _SHADOW_HIGHLIGHT_MAP["neutral"])

    # Protect skin tones when faces detected
    if has_faces:
        target_saturation = min(target_saturation, 0.6)
        blended_warmth = max(blended_warmth, 0.45)

    # Map to preset
    preset, strength = _map_mood_to_preset(
        primary_mood, blended_warmth, blended_intensity, vis_brightness, has_faces,
    )

    # Description
    description = _generate_description(primary_mood, blended_warmth, blended_intensity, preset)

    # Confidence — higher when audio signal is present
    audio_has_signal = (
        audio_mood.get("primary_mood") != "neutral"
        or audio_mood.get("intensity", 0) > 0.4
    )
    confidence = 0.85 if audio_has_signal else 0.55

    return {
        "mood": f"{primary_mood}_{'warm' if blended_warmth > 0.5 else 'cool'}",
        "target_brightness": target_brightness,
        "target_saturation": target_saturation,
        "target_contrast": target_contrast,
        "target_warmth": float(blended_warmth),
        "shadow_color": colors["shadow"],
        "highlight_color": colors["highlight"],
        "recommended_preset": preset,
        "recommended_strength": float(strength),
        "grade_description": description,
        "confidence": float(confidence),
        "audio_mood": primary_mood,
        "visual_scene": visual_analysis.get("scene_type", "general"),
        "has_faces": has_faces,
        "mood_tags": audio_mood.get("mood_tags", []) + visual_analysis.get("visual_tags", []),
    }


def _map_mood_to_preset(primary_mood, warmth, intensity, brightness, has_faces):
    """Map mood to the best preset and strength."""
    warmth_high = warmth > 0.5
    intensity_high = intensity > 0.5

    key = (primary_mood, warmth_high, intensity_high)
    preset, strength = _MOOD_PRESET_MAP.get(key, ("cinematic_warm", 0.5))

    # Lighter grade on faces
    if has_faces:
        strength *= 0.8

    # Don't crush already-dark footage further
    if brightness < 0.25 and preset == "moody_dark":
        strength *= 0.7

    return preset, float(np.clip(strength, 0.2, 0.9))


def _generate_description(mood, warmth, intensity, preset):
    """Generate a human-readable description of the chosen grade."""
    warmth_w = "warm" if warmth > 0.6 else "cool" if warmth < 0.4 else "balanced"
    intensity_w = "Dramatic" if intensity > 0.7 else "Subtle" if intensity < 0.3 else "Moderate"

    template = _GRADE_DESCRIPTIONS.get(preset, "{intensity}, {warmth_w} grade")
    return template.format(intensity=intensity_w, warmth_w=warmth_w)
