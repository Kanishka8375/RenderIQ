"""Preset listing and preview endpoints."""

import io
import os
import sys

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.schemas import PresetsListResponse, PresetInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from renderiq.presets_builder import list_presets as _list_presets, get_preset_path, PRESET_DEFINITIONS
from renderiq.lut_generator import load_cube
from renderiq.grader import apply_lut_to_frame
from renderiq.comparison import create_comparison

router = APIRouter(prefix="/api/presets", tags=["presets"])

# Category and color mapping for each preset
PRESET_META = {
    "cinematic_warm": {
        "category": "cinematic",
        "preview_colors": ["#2a1810", "#c47a3a", "#e8c07a"],
        "description": "Warm amber shadows, desaturated greens, golden highlights. Perfect for dramatic storytelling.",
    },
    "cinematic_cold": {
        "category": "cinematic",
        "preview_colors": ["#0d1b2a", "#1b4965", "#5fa8d3"],
        "description": "Cool teal shadows, blue midtones with subtle warmth in skin tones.",
    },
    "teal_orange": {
        "category": "cinematic",
        "preview_colors": ["#004e64", "#ff6b35", "#f0c808"],
        "description": "Classic blockbuster look with teal shadows and warm orange highlights.",
    },
    "vintage_film": {
        "category": "retro",
        "preview_colors": ["#3d2b1f", "#8b6f47", "#d4a574"],
        "description": "Faded film look with lifted blacks, slight magenta in shadows, and reduced saturation.",
    },
    "high_contrast_bw": {
        "category": "artistic",
        "preview_colors": ["#0a0a0a", "#808080", "#f5f5f5"],
        "description": "Dramatic black and white with deep blacks and bright whites.",
    },
    "moody_dark": {
        "category": "artistic",
        "preview_colors": ["#0a0e17", "#1a2332", "#3a4a5c"],
        "description": "Dark and brooding with crushed shadows, desaturation, and a cool blue tint.",
    },
    "pastel_soft": {
        "category": "lifestyle",
        "preview_colors": ["#b8d4e3", "#f2d7d5", "#d5e8d4"],
        "description": "Light and dreamy with lifted tones, reduced contrast, and soft pastels.",
    },
    "neon_night": {
        "category": "artistic",
        "preview_colors": ["#1a0533", "#7b2d8e", "#ff00ff"],
        "description": "Vibrant night look with boosted blues, purples, and magenta highlights.",
    },
    "golden_hour": {
        "category": "lifestyle",
        "preview_colors": ["#4a2c0a", "#d4880f", "#ffe08a"],
        "description": "Warm golden tones that replicate the magic of sunset lighting.",
    },
    "anime_vibrant": {
        "category": "artistic",
        "preview_colors": ["#1a1a2e", "#e94560", "#0f3460"],
        "description": "Ultra-vivid colors with boosted saturation and strong contrast for an animated look.",
    },
}


@router.get("", response_model=PresetsListResponse)
async def list_presets():
    """Return list of all available presets with metadata."""
    presets = []
    for name in PRESET_DEFINITIONS:
        meta = PRESET_META.get(name, {})
        presets.append(PresetInfo(
            name=name,
            display_name=PRESET_DEFINITIONS[name]["title"],
            description=meta.get("description", PRESET_DEFINITIONS[name]["description"]),
            category=meta.get("category", "other"),
            preview_colors=meta.get("preview_colors", ["#808080", "#808080", "#808080"]),
        ))
    return PresetsListResponse(presets=presets)


@router.get("/{name}/preview")
async def preset_preview(name: str):
    """Return a before/after preview image for a preset."""
    if name not in PRESET_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Preset not found: {name}")

    try:
        preset_path = get_preset_path(name)
        lut = load_cube(preset_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load preset: {e}")

    # Generate a stock test frame (gradient with colors)
    h, w = 360, 640
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = x / w
        r = int(180 * (1 - t) + 80 * t)
        g = int(120 + 40 * t)
        b = int(60 * (1 - t) + 200 * t)
        frame[:, x] = [r, g, b]

    graded = apply_lut_to_frame(frame, lut)
    comp = create_comparison(frame, graded, mode="side_by_side")

    # Encode as PNG
    bgr = cv2.cvtColor(comp, cv2.COLOR_RGB2BGR)
    success, buffer = cv2.imencode(".png", bgr)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode preview image")

    return StreamingResponse(
        io.BytesIO(buffer.tobytes()),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
