"""
Prompt Parser Module (Module 0)
Parse natural language editing prompts into structured edit plans.
Maps keywords to module activation flags.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Multi-word keyword mappings (checked first, in order of length)
MULTI_WORD_KEYWORDS = [
    # Speed ramp
    ("slow motion", {"speed_ramp": True, "pacing": "slow"}),
    ("speed ramp", {"speed_ramp": True}),
    ("speed up", {"speed_ramp": True, "pacing": "fast"}),
    ("dynamic camera", {"auto_zoom": True}),
    ("ken burns", {"auto_zoom": True}),
    # Reframe
    ("end card", {"end_text": "Follow for more"}),
    # Combined high-level prompts
    ("full edit", {
        "enhancement": True, "scene_detection": True, "smart_cuts": True,
        "transitions": True, "auto_zoom": True, "speed_ramp": True,
    }),
    ("cinematic edit", {
        "enhancement": True, "scene_detection": True, "smart_cuts": True,
        "transitions": True, "auto_zoom": True, "speed_ramp": True,
    }),
    ("full cinematic", {
        "enhancement": True, "scene_detection": True, "smart_cuts": True,
        "transitions": True, "auto_zoom": True, "speed_ramp": True,
    }),
    ("professional edit", {
        "enhancement": True, "transitions": True, "auto_zoom": True,
        "captions": True, "caption_style": "bold",
    }),
    ("social media", {
        "reframe": True, "reframe_ratio": "portrait", "captions": True,
        "caption_style": "viral", "pacing": "fast", "smart_cuts": True,
    }),
    ("golden hour", {"color_preset": "golden_hour"}),
    ("high contrast", {"color_preset": "high_contrast_bw"}),
]

# Single-word keyword mappings
SINGLE_WORD_KEYWORDS = {
    # Speed
    "slowmo": {"speed_ramp": True, "pacing": "slow"},
    "dynamic": {"speed_ramp": True, "transitions": True},
    # Transitions
    "smooth": {"transitions": True},
    "transitions": {"transitions": True},
    "professional": {"transitions": True, "enhancement": True, "auto_zoom": True},
    # Zoom
    "zoom": {"auto_zoom": True},
    # Reframe / platform
    "tiktok": {
        "reframe": True, "reframe_ratio": "portrait", "captions": True,
        "caption_style": "viral", "pacing": "fast",
    },
    "shorts": {"reframe": True, "reframe_ratio": "portrait", "pacing": "fast"},
    "reels": {"reframe": True, "reframe_ratio": "portrait", "pacing": "fast"},
    "instagram": {"reframe": True, "reframe_ratio": "instagram"},
    "vertical": {"reframe": True, "reframe_ratio": "portrait"},
    "portrait": {"reframe": True, "reframe_ratio": "portrait"},
    "square": {"reframe": True, "reframe_ratio": "square"},
    # Text
    "intro": {"title": "auto"},
    "title": {"title": "auto"},
    "subscribe": {"end_text": "Subscribe for more"},
    # Captions
    "captions": {"captions": True},
    "subtitles": {"captions": True},
    "caption": {"captions": True},
    # Enhancement
    "enhance": {"enhancement": True},
    "clean": {"enhancement": True},
    "denoise": {"enhancement": True},
    # Color presets
    "cinematic": {"color_preset": "cinematic_warm"},
    "warm": {"color_preset": "cinematic_warm"},
    "cold": {"color_preset": "cinematic_cold"},
    "cool": {"color_preset": "cinematic_cold"},
    "teal": {"color_preset": "teal_orange"},
    "vintage": {"color_preset": "vintage_film"},
    "retro": {"color_preset": "vintage_film"},
    "moody": {"color_preset": "moody_dark", "pacing": "slow"},
    "dark": {"color_preset": "moody_dark"},
    "pastel": {"color_preset": "pastel_soft"},
    "dreamy": {"color_preset": "pastel_soft"},
    "neon": {"color_preset": "neon_night"},
    "golden": {"color_preset": "golden_hour"},
    "anime": {"color_preset": "anime_vibrant"},
    "vibrant": {"color_preset": "anime_vibrant"},
    # Pacing
    "fast": {"pacing": "fast"},
    "slow": {"pacing": "slow"},
    "quick": {"pacing": "fast"},
    "dramatic": {"pacing": "slow", "color_preset": "moody_dark"},
    # Editing
    "montage": {"smart_cuts": True, "speed_ramp": True, "transitions": True},
    "highlight": {"smart_cuts": True, "pacing": "fast"},
    "highlights": {"smart_cuts": True, "pacing": "fast"},
    "cuts": {"smart_cuts": True},
    "edit": {"smart_cuts": True, "transitions": True},
    "music": {"music_sync": True},
    "beat": {"music_sync": True},
    "beats": {"music_sync": True},
}

# Suggestion chips with display text and full prompts
SUGGESTION_CHIPS = [
    {
        "label": "Full Cinematic Edit",
        "icon": "film",
        "prompt": "Make this a full cinematic edit with transitions and dramatic pacing",
    },
    {
        "label": "Fast Montage",
        "icon": "zap",
        "prompt": "Create a fast-paced montage with speed ramps and quick cuts",
    },
    {
        "label": "TikTok Ready",
        "icon": "smartphone",
        "prompt": "Make this vertical for TikTok with viral captions and fast pacing",
    },
    {
        "label": "Warm & Golden",
        "icon": "sun",
        "prompt": "Apply warm golden hour color grading with smooth transitions",
    },
    {
        "label": "Dark & Moody",
        "icon": "moon",
        "prompt": "Dark moody edit with slow pacing and dramatic zoom effects",
    },
    {
        "label": "Professional Edit",
        "icon": "video",
        "prompt": "Professional edit with auto enhancement, captions, and clean transitions",
    },
    {
        "label": "Anime Vibrant",
        "icon": "palette",
        "prompt": "Anime style with vibrant colors, fast cuts, and dynamic speed ramps",
    },
    {
        "label": "Vintage Film",
        "icon": "camera",
        "prompt": "Vintage film look with faded colors and smooth slow pacing",
    },
    {
        "label": "Social Media Ready",
        "icon": "share",
        "prompt": "Vertical crop, viral captions, fast cuts — ready for Instagram and TikTok",
    },
    {
        "label": "Clean & Simple",
        "icon": "sparkles",
        "prompt": "Clean up the video with auto enhancement and subtle color grading",
    },
]


def parse_prompt(prompt: str) -> dict:
    """
    Parse a natural language editing prompt into a structured edit plan.

    Returns dict with module activation flags:
    {
        "original_prompt": "...",
        "color_preset": "cinematic_warm",
        "color_strength": 0.8,
        "pacing": "medium",
        "enhancement": True/False,
        "scene_detection": True,
        "smart_cuts": True/False,
        "music_sync": True/False,
        "speed_ramp": True/False,
        "transitions": True/False,
        "auto_zoom": True/False,
        "reframe": True/False,
        "reframe_ratio": "portrait",
        "captions": True/False,
        "caption_style": "bold",
        "title": None or str,
        "subtitle": None,
        "end_text": None or str,
    }
    """
    prompt_lower = prompt.lower().strip()

    # Default plan
    plan = {
        "original_prompt": prompt,
        "color_preset": "cinematic_warm",
        "color_strength": 0.8,
        "pacing": "medium",
        "enhancement": False,
        "scene_detection": True,
        "smart_cuts": False,
        "music_sync": False,
        "speed_ramp": False,
        "transitions": False,
        "auto_zoom": False,
        "reframe": False,
        "reframe_ratio": "portrait",
        "captions": False,
        "caption_style": "bold",
        "title": None,
        "subtitle": None,
        "end_text": None,
    }

    # Check multi-word keywords first
    for keyword, flags in MULTI_WORD_KEYWORDS:
        if keyword in prompt_lower:
            plan.update(flags)

    # Check single-word keywords
    words = set(re.findall(r"\b\w+\b", prompt_lower))
    for word in words:
        if word in SINGLE_WORD_KEYWORDS:
            plan.update(SINGLE_WORD_KEYWORDS[word])

    # Parse strength if explicitly mentioned
    strength_match = re.search(r"(\d+)\s*%", prompt)
    if strength_match:
        plan["color_strength"] = min(1.0, int(strength_match.group(1)) / 100.0)

    # Auto-generate title from prompt if requested
    if plan.get("title") == "auto":
        plan["title"] = _auto_title(prompt_lower)

    # If no specific color preset was matched, keep default
    # If very minimal prompt, enable basic enhancements
    if len(words) <= 3 and not any(
        plan.get(k) for k in ["smart_cuts", "speed_ramp", "transitions", "reframe", "captions"]
    ):
        plan["enhancement"] = True

    logger.info("Parsed prompt: %s -> %d active modules", prompt[:50], _count_active(plan))

    return plan


def _auto_title(prompt_lower: str) -> Optional[str]:
    """Extract a meaningful title from the prompt."""
    stop_words = {
        "make", "this", "into", "a", "the", "my", "video", "edit", "like",
        "with", "and", "add", "for", "it", "to", "me", "please", "can",
        "you", "i", "want", "create", "give", "apply",
    }
    words = [w for w in prompt_lower.split() if w not in stop_words and len(w) > 2]
    if words:
        return " ".join(words[:5]).title()
    return None


def _count_active(plan: dict) -> int:
    """Count how many modules are active in the plan."""
    module_keys = [
        "enhancement", "scene_detection", "smart_cuts", "music_sync",
        "speed_ramp", "transitions", "auto_zoom", "reframe", "captions",
    ]
    return sum(1 for k in module_keys if plan.get(k))


def get_suggestion_chips() -> list:
    """Return the list of suggestion chips for the frontend."""
    return SUGGESTION_CHIPS
