"""Tests for smart_grade.visual_analyzer module."""

import numpy as np
import pytest

from renderiq.smart_grade.visual_analyzer import analyze_visual_content, _classify_scene


@pytest.fixture
def bright_warm_keyframes():
    """Create bright, warm-toned keyframes."""
    rng = np.random.default_rng(1)
    frames = []
    for i in range(5):
        frame = np.full((240, 320, 3), [220, 130, 50], dtype=np.uint8)
        noise = rng.integers(-10, 10, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frames.append({"frame": frame, "timestamp": float(i)})
    return frames


@pytest.fixture
def dark_cool_keyframes():
    """Create dark, cool-toned keyframes."""
    rng = np.random.default_rng(2)
    frames = []
    for i in range(5):
        frame = np.full((240, 320, 3), [30, 40, 80], dtype=np.uint8)
        noise = rng.integers(-5, 5, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frames.append({"frame": frame, "timestamp": float(i)})
    return frames


@pytest.fixture
def high_motion_keyframes():
    """Create keyframes with high inter-frame difference."""
    rng = np.random.default_rng(3)
    frames = []
    for i in range(10):
        # Alternate between very different frames
        base = 200 if i % 2 == 0 else 50
        frame = np.full((240, 320, 3), base, dtype=np.uint8)
        noise = rng.integers(-20, 20, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frames.append({"frame": frame, "timestamp": float(i)})
    return frames


class TestAnalyzeVisualContent:
    def test_returns_all_required_fields(self, bright_warm_keyframes):
        result = analyze_visual_content(bright_warm_keyframes)
        required = [
            "scene_type", "brightness", "saturation_level", "contrast_level",
            "warmth", "dominant_hue", "color_variety", "has_faces",
            "motion_level", "visual_tags",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_brightness_range(self, bright_warm_keyframes, dark_cool_keyframes):
        bright = analyze_visual_content(bright_warm_keyframes)
        dark = analyze_visual_content(dark_cool_keyframes)
        assert 0 <= bright["brightness"] <= 1
        assert 0 <= dark["brightness"] <= 1
        assert bright["brightness"] > dark["brightness"]

    def test_warmth_detection(self, bright_warm_keyframes, dark_cool_keyframes):
        warm = analyze_visual_content(bright_warm_keyframes)
        cool = analyze_visual_content(dark_cool_keyframes)
        assert warm["warmth"] > cool["warmth"]

    def test_motion_detection(self, high_motion_keyframes, bright_warm_keyframes):
        high_motion = analyze_visual_content(high_motion_keyframes)
        static = analyze_visual_content(bright_warm_keyframes)
        assert high_motion["motion_level"] > static["motion_level"]

    def test_visual_tags_are_strings(self, bright_warm_keyframes):
        result = analyze_visual_content(bright_warm_keyframes)
        assert isinstance(result["visual_tags"], list)
        for tag in result["visual_tags"]:
            assert isinstance(tag, str)

    def test_empty_keyframes_raises(self):
        with pytest.raises(ValueError, match="No keyframes"):
            analyze_visual_content([])


class TestClassifyScene:
    def test_night_scene(self):
        assert _classify_scene(0.1, 0.4, 0.5, False, 0.2, "blue") == "night"

    def test_low_light_scene(self):
        assert _classify_scene(0.15, 0.1, 0.5, False, 0.2, "neutral") == "low_light"

    def test_portrait_scene(self):
        assert _classify_scene(0.5, 0.4, 0.5, True, 0.1, "orange") == "portrait"

    def test_action_scene(self):
        assert _classify_scene(0.5, 0.4, 0.5, False, 0.7, "red") == "action"

    def test_nature_scene(self):
        assert _classify_scene(0.5, 0.6, 0.5, False, 0.2, "green") == "nature"

    def test_outdoor_warm(self):
        assert _classify_scene(0.7, 0.3, 0.6, False, 0.2, "orange") == "outdoor_warm"
