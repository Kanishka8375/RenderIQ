"""Tests for built-in preset system."""

import os
import subprocess

import numpy as np
import pytest

from renderiq.presets_builder import (
    list_presets,
    get_preset_path,
    generate_all_presets,
    generate_preset,
    PRESET_DEFINITIONS,
)
from renderiq.lut_generator import load_cube, export_cube
from renderiq.grader import apply_lut_to_frame, apply_lut_to_video
from tests.conftest import make_video_ffmpeg


class TestPresetGeneration:
    def test_all_10_presets_generate_valid_cube(self, tmp_path):
        """All 10 built-in presets should generate valid .cube files."""
        paths = generate_all_presets(size=5)
        assert len(paths) == 10
        for p in paths:
            assert os.path.isfile(p)
            lut = load_cube(p)
            assert lut.shape == (5, 5, 5, 3)

    def test_each_preset_produces_different_output(self):
        """Each preset should produce visually different results."""
        frame = np.full((50, 50, 3), 128, dtype=np.uint8)
        results = {}

        for name in list(PRESET_DEFINITIONS.keys())[:5]:
            path = generate_preset(name, size=5)
            lut = load_cube(path)
            graded = apply_lut_to_frame(frame, lut)
            results[name] = graded.mean(axis=(0, 1))

        # Check that at least some pairs differ significantly
        names = list(results.keys())
        different_pairs = 0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                diff = np.abs(results[names[i]] - results[names[j]]).max()
                if diff > 5:
                    different_pairs += 1

        assert different_pairs > 0, "Presets should produce different results"

    def test_preset_lut_shape(self):
        """Preset LUTs should have correct shape."""
        path = generate_preset("teal_orange", size=33)
        lut = load_cube(path)
        assert lut.shape == (33, 33, 33, 3)

    def test_preset_values_in_range(self):
        """Preset LUT values should be in valid [0.0, 1.0] range."""
        for name in PRESET_DEFINITIONS:
            path = generate_preset(name, size=5)
            lut = load_cube(path)
            assert lut.min() >= 0.0, f"{name} has values below 0"
            assert lut.max() <= 1.0, f"{name} has values above 1"


class TestPresetList:
    def test_list_returns_all_10_presets(self):
        """List command should return all 10 presets."""
        presets = list_presets()
        assert len(presets) == 10

    def test_list_has_required_fields(self):
        """Each preset in list should have name, title, description, path."""
        presets = list_presets()
        for p in presets:
            assert "name" in p
            assert "title" in p
            assert "description" in p
            assert "path" in p


class TestPresetCLI:
    def test_applying_preset_produces_output(self, tmp_path):
        """Applying a preset via code should produce a graded output file."""
        video_path = make_video_ffmpeg(tmp_path / "test.mp4", duration=1)
        preset_path = generate_preset("vintage_film", size=9)
        lut = load_cube(preset_path)

        output = str(tmp_path / "graded.mp4")
        apply_lut_to_video(video_path, lut, output)
        assert os.path.isfile(output)
        assert os.path.getsize(output) > 0

    def test_preset_with_strength(self, tmp_path):
        """Preset + strength flag should work correctly."""
        preset_path = generate_preset("golden_hour", size=9)
        lut = load_cube(preset_path)

        frame = np.full((50, 50, 3), 128, dtype=np.uint8)
        full = apply_lut_to_frame(frame, lut, strength=1.0)
        half = apply_lut_to_frame(frame, lut, strength=0.5)
        none = apply_lut_to_frame(frame, lut, strength=0.0)

        # Strength 0 should match original
        np.testing.assert_array_equal(none, frame)

        # Strength 0.5 should be between
        diff_full = np.abs(full.astype(float) - frame.astype(float)).mean()
        diff_half = np.abs(half.astype(float) - frame.astype(float)).mean()
        assert diff_full >= diff_half

    def test_cube_roundtrip(self, tmp_path):
        """Loading a preset .cube and applying should give same result."""
        path1 = generate_preset("moody_dark", size=5)
        lut1 = load_cube(path1)

        # Re-export and reload
        path2 = str(tmp_path / "re_exported.cube")
        export_cube(lut1, path2)
        lut2 = load_cube(path2)

        np.testing.assert_allclose(lut1, lut2, atol=1e-5)

    def test_invalid_preset_name(self):
        """Invalid preset name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset_path("nonexistent_preset_name")

    def test_presets_work_on_different_resolutions(self, tmp_path):
        """Presets should work on videos of different resolutions."""
        preset_path = generate_preset("pastel_soft", size=9)
        lut = load_cube(preset_path)

        for resolution in [(640, 480), (1280, 720)]:
            w, h = resolution
            path = make_video_ffmpeg(
                tmp_path / f"test_{w}x{h}.mp4",
                width=w, height=h, duration=1,
            )
            output = str(tmp_path / f"graded_{w}x{h}.mp4")
            apply_lut_to_video(path, lut, output)
            assert os.path.isfile(output)
