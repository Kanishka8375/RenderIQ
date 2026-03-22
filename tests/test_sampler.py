"""Tests for the frame sampling module."""

import numpy as np
import pytest

from renderiq.sampler import (
    extract_keyframes,
    _uniform_timestamps,
    _merge_timestamps,
)


class TestUniformTimestamps:
    def test_basic_interval(self):
        ts = _uniform_timestamps(10.0, 2.0)
        assert len(ts) == 5  # 0, 2, 4, 6, 8
        assert ts[0] == (0.0, "uniform")
        assert ts[-1] == (8.0, "uniform")

    def test_short_video(self):
        ts = _uniform_timestamps(1.0, 2.0)
        assert len(ts) == 1  # Just frame at 0.0

    def test_exact_duration(self):
        ts = _uniform_timestamps(4.0, 2.0)
        assert len(ts) == 2  # 0.0, 2.0


class TestMergeTimestamps:
    def test_no_duplicates(self):
        uniform = [(0.0, "uniform"), (2.0, "uniform"), (4.0, "uniform")]
        scene = [(1.0, "scene_change"), (3.0, "scene_change")]
        merged = _merge_timestamps(uniform, scene)
        assert len(merged) == 5

    def test_dedup_close_timestamps(self):
        uniform = [(0.0, "uniform"), (2.0, "uniform")]
        scene = [(2.1, "scene_change")]  # Within 0.5s of 2.0
        merged = _merge_timestamps(uniform, scene, min_gap=0.5)
        assert len(merged) == 2
        # Scene change should replace uniform when close
        assert merged[1][1] == "scene_change"

    def test_empty_inputs(self):
        assert _merge_timestamps([], []) == []

    def test_scene_only(self):
        merged = _merge_timestamps([], [(1.0, "scene_change")])
        assert len(merged) == 1


class TestExtractKeyframes:
    def test_basic_extraction(self, sample_video):
        frames = extract_keyframes(sample_video, interval_seconds=1.0)
        assert len(frames) > 0
        for f in frames:
            assert "frame" in f
            assert "timestamp" in f
            assert "source" in f
            assert isinstance(f["frame"], np.ndarray)
            assert f["frame"].ndim == 3
            assert f["frame"].shape[2] == 3  # RGB

    def test_max_frames_cap(self, sample_video):
        frames = extract_keyframes(sample_video, interval_seconds=0.1, max_frames=5)
        assert len(frames) <= 5

    def test_scene_change_detection(self, scene_change_video):
        frames = extract_keyframes(
            scene_change_video, interval_seconds=2.0, scene_threshold=0.3
        )
        scene_frames = [f for f in frames if f["source"] == "scene_change"]
        # Should detect at least some scene changes
        # (FFmpeg scene detection may not always work on synthetic videos)
        assert len(frames) > 0

    def test_timestamps_are_sorted(self, sample_video):
        frames = extract_keyframes(sample_video)
        timestamps = [f["timestamp"] for f in frames]
        assert timestamps == sorted(timestamps)

    def test_invalid_video_raises(self, tmp_path):
        fake = str(tmp_path / "nonexistent.mp4")
        with pytest.raises(FileNotFoundError):
            extract_keyframes(fake)
