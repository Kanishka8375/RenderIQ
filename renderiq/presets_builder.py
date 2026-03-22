"""Algorithmic preset LUT generation.

Generates 10 built-in color grade presets using pure math —
no reference video needed. Each preset is defined by LAB channel
transfer curves that produce a specific aesthetic.
"""

import logging
import os

import numpy as np

from renderiq.lut_generator import generate_lut_from_curves, export_cube

logger = logging.getLogger(__name__)

PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets", "builtin")

PRESET_DEFINITIONS = {
    "cinematic_warm": {
        "title": "Cinematic Warm",
        "description": "Lift shadows toward orange/amber, desaturate greens, warm highlights",
    },
    "cinematic_cold": {
        "title": "Cinematic Cold",
        "description": "Push shadows toward teal/blue, cool midtones, slightly warm skin tones",
    },
    "teal_orange": {
        "title": "Teal & Orange",
        "description": "Classic blockbuster look: teal shadows + orange highlights",
    },
    "vintage_film": {
        "title": "Vintage Film",
        "description": "Lifted blacks, slight magenta in shadows, reduced saturation, warm overall",
    },
    "high_contrast_bw": {
        "title": "High Contrast B&W",
        "description": "Convert to black and white with strong contrast",
    },
    "moody_dark": {
        "title": "Moody Dark",
        "description": "Crush shadows aggressively, desaturate, slight blue tint",
    },
    "pastel_soft": {
        "title": "Pastel Soft",
        "description": "Lift everything, reduce contrast, boost pastel tones, dreamy feel",
    },
    "neon_night": {
        "title": "Neon Night",
        "description": "Boost blues and purples in shadows, boost magentas in highlights",
    },
    "golden_hour": {
        "title": "Golden Hour",
        "description": "Strong warm shift, orange/gold highlights, soft shadows",
    },
    "anime_vibrant": {
        "title": "Anime Vibrant",
        "description": "Boost saturation significantly, strong contrast, vivid colors",
    },
}


def list_presets() -> list[dict]:
    """Return list of available built-in presets with metadata."""
    result = []
    for name, info in PRESET_DEFINITIONS.items():
        cube_path = os.path.join(PRESETS_DIR, f"{name}.cube")
        result.append({
            "name": name,
            "title": info["title"],
            "description": info["description"],
            "path": cube_path,
            "exists": os.path.isfile(cube_path),
        })
    return result


def get_preset_path(name: str) -> str:
    """Get path to a built-in preset .cube file, generating if needed.

    Args:
        name: Preset name (e.g. 'cinematic_warm').

    Returns:
        Path to the .cube file.

    Raises:
        ValueError: If preset name is not recognized.
    """
    if name not in PRESET_DEFINITIONS:
        available = ", ".join(sorted(PRESET_DEFINITIONS.keys()))
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")

    cube_path = os.path.join(PRESETS_DIR, f"{name}.cube")
    if not os.path.isfile(cube_path):
        generate_preset(name)
    return cube_path


def generate_all_presets(size: int = 33) -> list[str]:
    """Generate all 10 built-in preset .cube files.

    Args:
        size: LUT grid size (default 33).

    Returns:
        List of generated file paths.
    """
    os.makedirs(PRESETS_DIR, exist_ok=True)
    paths = []
    for name in PRESET_DEFINITIONS:
        path = generate_preset(name, size=size)
        paths.append(path)
    return paths


def generate_preset(name: str, size: int = 33) -> str:
    """Generate a single preset .cube file.

    Args:
        name: Preset name.
        size: LUT grid size.

    Returns:
        Path to the generated .cube file.
    """
    if name not in PRESET_DEFINITIONS:
        available = ", ".join(sorted(PRESET_DEFINITIONS.keys()))
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")

    l_curve, a_curve, b_curve = _build_curves(name)
    lut = generate_lut_from_curves(l_curve, a_curve, b_curve, size=size)

    os.makedirs(PRESETS_DIR, exist_ok=True)
    cube_path = os.path.join(PRESETS_DIR, f"{name}.cube")
    export_cube(lut, cube_path, title=PRESET_DEFINITIONS[name]["title"])
    logger.info("Generated preset: %s -> %s", name, cube_path)
    return cube_path


def _build_curves(name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build LAB channel curves for a named preset.

    Returns:
        Tuple of (L_curve, A_curve, B_curve), each 256-element float arrays.
    """
    x = np.arange(256, dtype=np.float64)
    identity = x.copy()

    if name == "cinematic_warm":
        # Lift shadows, warm overall
        l_curve = _apply_lift_gamma_gain(x, lift=15, gamma=1.05, gain=0.98)
        # Push A toward red (higher A = more red/magenta)
        a_curve = identity + 5
        # Push B toward yellow (higher B = more yellow)
        b_curve = identity + 10
        # Reduce green in midtones
        a_curve = np.where(x < 128, a_curve + 3, a_curve)

    elif name == "cinematic_cold":
        # Cool tones
        l_curve = _apply_lift_gamma_gain(x, lift=5, gamma=1.02, gain=0.97)
        # Push toward green/cyan in shadows (lower A)
        a_curve = identity - 6
        # Push toward blue in shadows (lower B)
        b_curve = identity.copy()
        b_curve = np.where(x < 128, b_curve - 12, b_curve - 3)

    elif name == "teal_orange":
        # Classic blockbuster
        l_curve = _apply_lift_gamma_gain(x, lift=5, gamma=1.0, gain=1.0)
        # Shadows green/teal (low A), highlights warm (high A)
        a_curve = identity.copy()
        a_curve = np.where(x < 100, a_curve - 10, a_curve)
        a_curve = np.where(x > 160, a_curve + 8, a_curve)
        # Shadows blue (low B), highlights orange (high B)
        b_curve = identity.copy()
        b_curve = np.where(x < 100, b_curve - 15, b_curve)
        b_curve = np.where(x > 160, b_curve + 12, b_curve)

    elif name == "vintage_film":
        # Lifted blacks, faded look
        l_curve = _apply_lift_gamma_gain(x, lift=30, gamma=0.95, gain=0.92)
        # Slight magenta in shadows
        a_curve = identity.copy()
        a_curve = np.where(x < 100, a_curve + 5, a_curve)
        # Warm overall, reduced range
        b_curve = identity * 0.9 + 12

    elif name == "high_contrast_bw":
        # B&W via desaturation in LAB: A and B go to neutral (128)
        # Strong S-curve on L for contrast
        l_curve = _s_curve(x, strength=1.5)
        a_curve = np.full(256, 128.0)  # Neutral = no color
        b_curve = np.full(256, 128.0)

    elif name == "moody_dark":
        # Crush shadows, desaturate, blue tint
        l_curve = _apply_lift_gamma_gain(x, lift=0, gamma=1.2, gain=0.85)
        # Desaturate by pushing toward neutral
        a_curve = identity * 0.7 + 128 * 0.3
        b_curve = identity * 0.7 + 128 * 0.3
        # Slight blue tint
        b_curve -= 5

    elif name == "pastel_soft":
        # Lift everything, reduce contrast, dreamy
        l_curve = _apply_lift_gamma_gain(x, lift=40, gamma=0.85, gain=0.95)
        # Slight pastel shift
        a_curve = identity * 0.8 + 128 * 0.2
        b_curve = identity * 0.8 + 128 * 0.2 + 3

    elif name == "neon_night":
        # Boost blues/purples in shadows, magentas in highlights
        l_curve = _apply_lift_gamma_gain(x, lift=5, gamma=1.05, gain=1.0)
        # Push A toward magenta/red
        a_curve = identity + 10
        # Push B toward blue in shadows, keep in highlights
        b_curve = identity.copy()
        b_curve = np.where(x < 128, b_curve - 18, b_curve + 5)

    elif name == "golden_hour":
        # Strong warm, orange/gold
        l_curve = _apply_lift_gamma_gain(x, lift=10, gamma=0.95, gain=1.0)
        # Warm = push A slightly toward red
        a_curve = identity + 4
        # Strong push toward yellow
        b_curve = identity + 18

    elif name == "anime_vibrant":
        # Boost saturation via expanding A and B range, strong contrast
        l_curve = _s_curve(x, strength=1.2)
        # Expand A and B to boost saturation
        a_curve = (identity - 128) * 1.4 + 128
        b_curve = (identity - 128) * 1.4 + 128

    else:
        l_curve = identity
        a_curve = identity
        b_curve = identity

    # Clamp all curves to valid range
    l_curve = np.clip(l_curve, 0, 255)
    a_curve = np.clip(a_curve, 0, 255)
    b_curve = np.clip(b_curve, 0, 255)

    return l_curve, a_curve, b_curve


def _apply_lift_gamma_gain(
    x: np.ndarray, lift: float = 0, gamma: float = 1.0, gain: float = 1.0
) -> np.ndarray:
    """Apply lift/gamma/gain color correction curve.

    lift: Added to shadows (shifts black point up).
    gamma: Power curve (>1 = darker midtones, <1 = brighter midtones).
    gain: Multiplier on highlights.
    """
    normalized = x / 255.0
    # Apply gain
    result = normalized * gain
    # Apply gamma
    result = np.clip(result, 0, 1) ** gamma
    # Apply lift
    result = result * 255.0 + lift
    return np.clip(result, 0, 255)


def _s_curve(x: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Apply an S-curve for contrast enhancement.

    strength > 1.0 = more contrast, < 1.0 = less contrast.
    """
    normalized = x / 255.0
    # Sigmoid-based S-curve centered at 0.5
    centered = normalized - 0.5
    result = 0.5 + centered * np.abs(centered) ** (strength - 1) * strength
    result = np.clip(result, 0, 1)
    return result * 255.0
