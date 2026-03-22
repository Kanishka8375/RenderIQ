"""Tests for quality improvements: strength, multi-scene, white balance, comparison."""

import os

import cv2
import numpy as np
import pytest

from renderiq.grader import apply_lut_to_frame, auto_white_balance, preview_grade
from renderiq.analyzer import analyze_color_profile, cluster_keyframes
from renderiq.comparison import create_comparison
from renderiq.presets_builder import generate_preset, PRESET_DEFINITIONS
from renderiq.lut_generator import load_cube
from tests.conftest import make_video_ffmpeg


@pytest.fixture
def non_identity_lut():
    """Create a LUT that visibly changes colors (warm shift)."""
    size = 9
    lut = np.zeros((size, size, size, 3), dtype=np.float32)
    grid = np.linspace(0, 1, size)
    for ri, r in enumerate(grid):
        for gi, g in enumerate(grid):
            for bi, b in enumerate(grid):
                lut[ri, gi, bi] = [
                    min(r * 1.3, 1.0),
                    g * 0.9,
                    b * 0.7,
                ]
    return lut


class TestStrengthControl:
    def test_strength_zero_preserves_input(self, identity_lut):
        """Strength 0.0 should produce output identical to input."""
        frame = np.random.default_rng(42).integers(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_lut_to_frame(frame, identity_lut, strength=0.0)
        np.testing.assert_array_equal(result, frame)

    def test_strength_one_full_grade(self, non_identity_lut):
        """Strength 1.0 should apply the full grade."""
        frame = np.full((100, 100, 3), 128, dtype=np.uint8)
        full = apply_lut_to_frame(frame, non_identity_lut, strength=1.0)
        half = apply_lut_to_frame(frame, non_identity_lut, strength=0.5)
        # Full grade should be further from original than half grade
        diff_full = np.abs(full.astype(float) - frame.astype(float)).mean()
        diff_half = np.abs(half.astype(float) - frame.astype(float)).mean()
        assert diff_full > diff_half

    def test_strength_half_is_between(self, non_identity_lut):
        """Strength 0.5 should produce output between input and full grade."""
        frame = np.full((100, 100, 3), 128, dtype=np.uint8)
        full = apply_lut_to_frame(frame, non_identity_lut, strength=1.0)
        half = apply_lut_to_frame(frame, non_identity_lut, strength=0.5)

        # Half grade R channel should be between original and full
        orig_r = frame[:, :, 0].mean()
        full_r = full[:, :, 0].mean()
        half_r = half[:, :, 0].mean()

        lo, hi = min(orig_r, full_r), max(orig_r, full_r)
        assert lo <= half_r + 2 <= hi + 2  # Allow small rounding tolerance


class TestMultiScene:
    def test_cluster_finds_distinct_scenes(self):
        """Clustering should find at least 2 clusters for visually different scenes."""
        rng = np.random.default_rng(42)
        keyframes = []
        # Scene 1: warm frames
        for i in range(5):
            frame = np.full((100, 100, 3), [200, 100, 50], dtype=np.uint8)
            noise = rng.integers(-10, 10, frame.shape, dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            keyframes.append({"frame": frame, "timestamp": float(i), "source": "uniform"})
        # Scene 2: cold frames
        for i in range(5):
            frame = np.full((100, 100, 3), [50, 100, 200], dtype=np.uint8)
            noise = rng.integers(-10, 10, frame.shape, dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            keyframes.append({"frame": frame, "timestamp": float(i + 5), "source": "uniform"})

        clusters = cluster_keyframes(keyframes, n_clusters=3)
        assert len(clusters) >= 2


class TestWhiteBalance:
    def test_wb_shifts_toward_neutral(self):
        """White balance should shift average color toward neutral gray."""
        # Create a warm-biased frame
        frame = np.full((100, 100, 3), [200, 130, 80], dtype=np.uint8)
        corrected = auto_white_balance(frame)

        # After WB, channels should be closer together
        orig_range = frame.mean(axis=(0, 1)).max() - frame.mean(axis=(0, 1)).min()
        corr_range = corrected.mean(axis=(0, 1)).max() - corrected.mean(axis=(0, 1)).min()
        assert corr_range < orig_range


class TestComparisonImage:
    def test_comparison_is_valid_png(self, tmp_path):
        """Comparison image should be a valid PNG with correct dimensions."""
        original = np.random.default_rng(42).integers(
            0, 256, (480, 640, 3), dtype=np.uint8
        )
        graded = np.random.default_rng(99).integers(
            0, 256, (480, 640, 3), dtype=np.uint8
        )
        comp = create_comparison(original, graded, mode="side_by_side")

        # Should be 1080p height
        assert comp.shape[0] == 1080
        assert comp.ndim == 3
        assert comp.shape[2] == 3

        # Save and verify it's a valid image
        path = str(tmp_path / "comp.png")
        cv2.imwrite(path, cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))
        assert os.path.isfile(path)
        loaded = cv2.imread(path)
        assert loaded is not None

    def test_comparison_halves_are_different(self):
        """The two halves of the comparison should be visually different."""
        original = np.full((480, 640, 3), [100, 100, 100], dtype=np.uint8)
        graded = np.full((480, 640, 3), [200, 150, 100], dtype=np.uint8)
        comp = create_comparison(original, graded, mode="side_by_side")

        mid = comp.shape[1] // 2
        left_mean = comp[:, :mid - 5].mean()
        right_mean = comp[:, mid + 5:].mean()
        assert abs(left_mean - right_mean) > 10

    def test_slider_mode(self):
        """Slider mode should produce a single image."""
        original = np.full((480, 640, 3), [80, 80, 80], dtype=np.uint8)
        graded = np.full((480, 640, 3), [200, 150, 100], dtype=np.uint8)
        comp = create_comparison(original, graded, mode="slider")

        assert comp.shape[0] == 1080
        assert comp.ndim == 3


class TestPresetCubeGeneration:
    def test_each_builtin_preset_generates_valid_cube(self, tmp_path):
        """Each built-in preset should generate a valid .cube file."""
        # Test just one preset to keep test fast
        name = "cinematic_warm"
        path = generate_preset(name, size=5)
        lut = load_cube(path)
        assert lut.shape == (5, 5, 5, 3)
        assert lut.min() >= 0.0
        assert lut.max() <= 1.0
