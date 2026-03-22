"""Tests for the video grading module."""

import os

import cv2
import numpy as np
import pytest

from renderiq.grader import apply_lut_to_frame, apply_lut_to_video, preview_grade


class TestApplyLutToFrame:
    def test_identity_lut_preserves_frame(self, identity_lut):
        """An identity LUT should not significantly change the frame."""
        frame = np.full((100, 100, 3), [128, 128, 128], dtype=np.uint8)
        result = apply_lut_to_frame(frame, identity_lut)

        assert result.shape == frame.shape
        assert result.dtype == np.uint8
        # Should be very close to original with identity LUT
        diff = np.abs(result.astype(int) - frame.astype(int)).mean()
        assert diff < 5, f"Mean diff with identity LUT: {diff}"

    def test_output_range(self, identity_lut):
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_lut_to_frame(frame, identity_lut)
        assert result.min() >= 0
        assert result.max() <= 255

    def test_different_lut_changes_colors(self):
        """A non-identity LUT should change colors."""
        size = 9
        # Create a LUT that boosts red channel
        lut = np.zeros((size, size, size, 3), dtype=np.float32)
        grid = np.linspace(0, 1, size)
        for ri, r in enumerate(grid):
            for gi, g in enumerate(grid):
                for bi, b in enumerate(grid):
                    lut[ri, gi, bi] = [min(r * 1.5, 1.0), g * 0.8, b * 0.8]

        frame = np.full((50, 50, 3), [100, 100, 100], dtype=np.uint8)
        result = apply_lut_to_frame(frame, lut)

        # Red channel should be boosted
        assert result[:, :, 0].mean() > frame[:, :, 0].mean()

    def test_black_frame(self, identity_lut):
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        result = apply_lut_to_frame(frame, identity_lut)
        assert result.mean() < 5

    def test_white_frame(self, identity_lut):
        frame = np.full((50, 50, 3), 255, dtype=np.uint8)
        result = apply_lut_to_frame(frame, identity_lut)
        assert result.mean() > 250


class TestApplyLutToVideo:
    def test_basic_grading(self, sample_video, identity_lut, tmp_path):
        output = str(tmp_path / "graded.mp4")
        result = apply_lut_to_video(sample_video, identity_lut, output)
        assert os.path.isfile(result)
        assert os.path.getsize(result) > 0

    def test_output_has_correct_dimensions(self, sample_video, identity_lut, tmp_path):
        output = str(tmp_path / "graded.mp4")
        apply_lut_to_video(sample_video, identity_lut, output)

        cap = cv2.VideoCapture(output)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Original is 320x240
        assert w == 320
        assert h == 240


class TestPreviewGrade:
    def test_preview_returns_two_frames(self, sample_video, identity_lut):
        original, graded = preview_grade(sample_video, identity_lut, timestamp=1.0)
        assert original.shape == graded.shape
        assert original.ndim == 3
        assert original.shape[2] == 3

    def test_preview_default_timestamp(self, sample_video, identity_lut):
        original, graded = preview_grade(sample_video, identity_lut)
        assert original is not None
        assert graded is not None
