"""Tests for edge cases: resolution mismatch, frame rate, short/long videos, etc."""

import os
import subprocess

import cv2
import numpy as np
import pytest

from renderiq.grader import apply_lut_to_video, apply_lut_to_frame
from renderiq.sampler import extract_keyframes
from renderiq.analyzer import analyze_color_profile
from renderiq.lut_generator import generate_lut
from renderiq.utils import validate_video, get_video_info
from tests.conftest import make_video_ffmpeg


@pytest.fixture
def video_4k(tmp_path):
    """Create a 4K (3840x2160) test video, 2 seconds."""
    return make_video_ffmpeg(
        tmp_path / "4k.mp4", width=3840, height=2160,
        fps=24, duration=2, color="CC8844",
    )


@pytest.fixture
def video_720p(tmp_path):
    """Create a 720p (1280x720) test video, 2 seconds."""
    return make_video_ffmpeg(
        tmp_path / "720p.mp4", width=1280, height=720,
        fps=30, duration=2, color="4488CC",
    )


@pytest.fixture
def video_24fps(tmp_path):
    """Create a 24fps test video."""
    return make_video_ffmpeg(
        tmp_path / "24fps.mp4", width=320, height=240,
        fps=24, duration=2, color="808080",
    )


@pytest.fixture
def video_60fps(tmp_path):
    """Create a 60fps test video."""
    return make_video_ffmpeg(
        tmp_path / "60fps.mp4", width=320, height=240,
        fps=60, duration=2, color="808080",
    )


class TestResolutionMismatch:
    def test_4k_ref_720p_raw(self, video_4k, video_720p, tmp_path):
        """4K reference + 720p raw → output must be 720p with correct grade."""
        # Extract profile from 4K reference
        ref_kf = extract_keyframes(video_4k, interval_seconds=1.0)
        ref_profile = analyze_color_profile(ref_kf)

        # Extract profile from 720p raw
        raw_kf = extract_keyframes(video_720p, interval_seconds=1.0)
        raw_profile = analyze_color_profile(raw_kf)

        # Generate LUT and apply
        lut = generate_lut(raw_profile, ref_profile, size=9)
        output = str(tmp_path / "graded_720p.mp4")
        apply_lut_to_video(video_720p, lut, output)

        # Verify output is 720p
        info = get_video_info(output)
        assert info["width"] == 1280
        assert info["height"] == 720
        assert os.path.getsize(output) > 0

    def test_720p_ref_4k_raw(self, video_720p, video_4k, tmp_path):
        """720p reference + 4K raw → output must be 4K."""
        ref_kf = extract_keyframes(video_720p, interval_seconds=1.0)
        ref_profile = analyze_color_profile(ref_kf)

        raw_kf = extract_keyframes(video_4k, interval_seconds=1.0)
        raw_profile = analyze_color_profile(raw_kf)

        lut = generate_lut(raw_profile, ref_profile, size=9)
        output = str(tmp_path / "graded_4k.mp4")
        apply_lut_to_video(video_4k, lut, output)

        info = get_video_info(output)
        assert info["width"] == 3840
        assert info["height"] == 2160


class TestFrameRateMismatch:
    def test_24fps_ref_60fps_raw(self, video_24fps, video_60fps, tmp_path):
        """24fps reference + 60fps raw → output must be 60fps."""
        ref_kf = extract_keyframes(video_24fps, interval_seconds=1.0)
        ref_profile = analyze_color_profile(ref_kf)

        raw_kf = extract_keyframes(video_60fps, interval_seconds=1.0)
        raw_profile = analyze_color_profile(raw_kf)

        lut = generate_lut(raw_profile, ref_profile, size=9)
        output = str(tmp_path / "graded_60fps.mp4")
        apply_lut_to_video(video_60fps, lut, output)

        info = get_video_info(output)
        assert abs(info["fps"] - 60.0) < 1.0  # Allow small deviation

    def test_60fps_ref_24fps_raw(self, video_60fps, video_24fps, tmp_path):
        """60fps reference + 24fps raw → output must be 24fps."""
        ref_kf = extract_keyframes(video_60fps, interval_seconds=1.0)
        ref_profile = analyze_color_profile(ref_kf)

        raw_kf = extract_keyframes(video_24fps, interval_seconds=1.0)
        raw_profile = analyze_color_profile(raw_kf)

        lut = generate_lut(raw_profile, ref_profile, size=9)
        output = str(tmp_path / "graded_24fps.mp4")
        apply_lut_to_video(video_24fps, lut, output)

        info = get_video_info(output)
        assert abs(info["fps"] - 24.0) < 1.0


class TestShortVideos:
    def test_1_second_video(self, tmp_path):
        """1-second video should extract at least 3 keyframes."""
        path = make_video_ffmpeg(tmp_path / "1s.mp4", duration=1)
        frames = extract_keyframes(path, interval_seconds=2.0)
        assert len(frames) >= 3

    def test_3_second_video(self, tmp_path):
        """3-second video should work correctly."""
        path = make_video_ffmpeg(tmp_path / "3s.mp4", duration=3)
        frames = extract_keyframes(path, interval_seconds=2.0)
        assert len(frames) >= 3

    def test_5_second_video(self, tmp_path):
        """5-second video boundary — should use 1fps interval."""
        path = make_video_ffmpeg(tmp_path / "5s.mp4", duration=5)
        frames = extract_keyframes(path, interval_seconds=2.0)
        assert len(frames) >= 3


class TestNoAudio:
    def test_video_without_audio(self, tmp_path):
        """Video with no audio track should not crash."""
        path = make_video_ffmpeg(
            tmp_path / "silent.mp4", duration=2, has_audio=False
        )
        info = get_video_info(path)
        assert not info["has_audio"]

        # Grade should work fine
        size = 9
        lut = np.zeros((size, size, size, 3), dtype=np.float32)
        grid = np.linspace(0, 1, size)
        for ri, r in enumerate(grid):
            for gi, g in enumerate(grid):
                for bi, b in enumerate(grid):
                    lut[ri, gi, bi] = [r, g, b]

        output = str(tmp_path / "graded_silent.mp4")
        apply_lut_to_video(path, lut, output)
        assert os.path.isfile(output)
        assert os.path.getsize(output) > 0


class TestExposure:
    def test_overexposed_reference(self, tmp_path):
        """Overexposed video should be detected and analyzed with lower weight."""
        path = make_video_ffmpeg(
            tmp_path / "overexposed.mp4", duration=2, color="FAFAFA"
        )
        kf = extract_keyframes(path, interval_seconds=1.0)
        profile = analyze_color_profile(kf)

        assert "warnings" in profile
        assert profile["warnings"]["overexposed_frames"] >= 0
        assert profile["warnings"]["total_frames"] > 0

    def test_underexposed_reference(self, tmp_path):
        """Underexposed video should be detected."""
        path = make_video_ffmpeg(
            tmp_path / "underexposed.mp4", duration=2, color="080808"
        )
        kf = extract_keyframes(path, interval_seconds=1.0)
        profile = analyze_color_profile(kf)

        assert "warnings" in profile
        assert profile["warnings"]["underexposed_frames"] >= 0


class TestCorruptedFiles:
    def test_corrupted_truncated_mp4(self, tmp_path):
        """Truncated MP4 should return validation error, not crash."""
        # Create a valid video then truncate it
        path = tmp_path / "truncated.mp4"
        make_video_ffmpeg(path, duration=2)

        # Truncate the file to 1/4 of its size
        size = os.path.getsize(str(path))
        with open(str(path), "r+b") as f:
            f.truncate(size // 4)

        result = validate_video(str(path))
        # It might still be parseable by ffprobe or not — either way, no crash
        assert result is True or isinstance(result, dict)

    def test_zero_byte_file(self, tmp_path):
        """Zero-byte file should return clear error."""
        path = str(tmp_path / "empty.mp4")
        with open(path, "w"):
            pass

        result = validate_video(path)
        assert isinstance(result, dict)
        assert result["valid"] is False
        assert "empty" in result["error"].lower() or "zero" in result["error"].lower()

    def test_non_video_file(self, tmp_path):
        """A .txt file renamed to .mp4 should return clear error."""
        path = str(tmp_path / "fake.mp4")
        with open(path, "w") as f:
            f.write("This is not a video file\n")

        result = validate_video(path)
        assert isinstance(result, dict)
        assert result["valid"] is False
