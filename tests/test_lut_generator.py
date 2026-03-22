"""Tests for the 3D LUT generation and .cube file I/O."""

import os

import numpy as np
import pytest

from renderiq.analyzer import analyze_color_profile
from renderiq.lut_generator import generate_lut, export_cube, load_cube


class TestGenerateLut:
    def test_lut_shape(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)
        lut = generate_lut(profile, profile, size=9)
        assert lut.shape == (9, 9, 9, 3)
        assert lut.dtype == np.float32

    def test_lut_value_range(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)
        lut = generate_lut(profile, profile, size=9)
        assert lut.min() >= 0.0
        assert lut.max() <= 1.0

    def test_identical_profiles_near_identity(self, sample_keyframes):
        """When source and reference are the same, LUT should be near identity."""
        profile = analyze_color_profile(sample_keyframes)
        lut = generate_lut(profile, profile, size=9)

        # Build identity for comparison
        size = 9
        grid = np.linspace(0, 1, size, dtype=np.float32)
        identity = np.zeros((size, size, size, 3), dtype=np.float32)
        for ri, r in enumerate(grid):
            for gi, g in enumerate(grid):
                for bi, b in enumerate(grid):
                    identity[ri, gi, bi] = [r, g, b]

        # Should be close to identity (allow some tolerance due to
        # color space conversion round-trips)
        diff = np.abs(lut - identity).mean()
        assert diff < 0.25, f"Mean diff from identity: {diff}"


class TestCubeExport:
    def test_export_creates_file(self, identity_lut, tmp_path):
        path = str(tmp_path / "test.cube")
        result = export_cube(identity_lut, path)
        assert os.path.isfile(result)

    def test_cube_file_format(self, identity_lut, tmp_path):
        path = str(tmp_path / "test.cube")
        export_cube(identity_lut, path, title="Test LUT")

        with open(path) as f:
            content = f.read()

        assert 'TITLE "Test LUT"' in content
        assert "LUT_3D_SIZE 17" in content
        assert "DOMAIN_MIN 0.0 0.0 0.0" in content
        assert "DOMAIN_MAX 1.0 1.0 1.0" in content

        # Count data lines (excluding headers/blanks)
        data_lines = [
            l for l in content.strip().split("\n")
            if l and not l.startswith(("TITLE", "LUT_3D", "DOMAIN", "#"))
        ]
        assert len(data_lines) == 17 ** 3

    def test_cube_roundtrip(self, identity_lut, tmp_path):
        path = str(tmp_path / "roundtrip.cube")
        export_cube(identity_lut, path)
        loaded = load_cube(path)

        assert loaded.shape == identity_lut.shape
        np.testing.assert_allclose(loaded, identity_lut, atol=1e-5)


class TestCubeLoad:
    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_cube("/nonexistent/path.cube")

    def test_load_invalid_content(self, tmp_path):
        path = str(tmp_path / "bad.cube")
        with open(path, "w") as f:
            f.write("not a valid cube file\n")
        with pytest.raises(ValueError):
            load_cube(path)

    def test_load_valid_small_cube(self, tmp_path):
        """Create and load a minimal 2x2x2 cube file."""
        path = str(tmp_path / "small.cube")
        with open(path, "w") as f:
            f.write('TITLE "Small"\n')
            f.write("LUT_3D_SIZE 2\n")
            f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
            f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
            for r in range(2):
                for g in range(2):
                    for b in range(2):
                        f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")

        lut = load_cube(path)
        assert lut.shape == (2, 2, 2, 3)
