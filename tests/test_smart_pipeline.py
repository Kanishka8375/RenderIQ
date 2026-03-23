"""Tests for the smart_grade.smart_pipeline module."""

import os
import subprocess

import pytest


@pytest.fixture
def video_with_audio(tmp_path):
    """Create a test video with audio for smart grading."""
    path = str(tmp_path / "smart_test.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#C08040:s=320x240:d=3:r=24",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


@pytest.fixture
def video_no_audio(tmp_path):
    """Create a test video without audio for smart grading."""
    path = str(tmp_path / "smart_no_audio.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#4060C0:s=320x240:d=2:r=24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-an", path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


class TestSmartGrade:
    def test_smart_grade_with_audio(self, video_with_audio, tmp_path):
        from renderiq.smart_grade import smart_grade
        output = str(tmp_path / "graded.mp4")
        result = smart_grade(video_with_audio, output)

        assert os.path.exists(output)
        assert result["output_path"] == output
        assert "mood_profile" in result
        assert "audio_analysis" in result
        assert "visual_analysis" in result
        assert "grade_applied" in result
        assert result["audio_analysis"]["has_audio"] is True
        assert isinstance(result["processing_time"], float)
        assert result["processing_time"] > 0

    def test_smart_grade_no_audio(self, video_no_audio, tmp_path):
        from renderiq.smart_grade import smart_grade
        output = str(tmp_path / "graded_no_audio.mp4")
        result = smart_grade(video_no_audio, output)

        assert os.path.exists(output)
        assert result["audio_analysis"]["has_audio"] is False
        # Should still produce a valid grade
        assert result["grade_applied"]["preset"] is not None

    def test_progress_callback(self, video_with_audio, tmp_path):
        from renderiq.smart_grade import smart_grade
        output = str(tmp_path / "graded_cb.mp4")
        steps = []

        def cb(step, pct):
            steps.append((step, pct))

        smart_grade(video_with_audio, output, progress_callback=cb)
        assert len(steps) > 0
        # Progress should increase
        pcts = [s[1] for s in steps]
        assert pcts[-1] >= pcts[0]

    def test_strength_override(self, video_with_audio, tmp_path):
        from renderiq.smart_grade import smart_grade
        output = str(tmp_path / "graded_strength.mp4")
        result = smart_grade(video_with_audio, output, strength_override=0.3)
        assert result["grade_applied"]["strength"] == 0.3
        assert result["grade_applied"]["was_overridden"] is True

    def test_result_structure(self, video_with_audio, tmp_path):
        from renderiq.smart_grade import smart_grade
        output = str(tmp_path / "graded_struct.mp4")
        result = smart_grade(video_with_audio, output)

        # Check nested structure
        assert "scene_type" in result["visual_analysis"]
        assert "brightness" in result["visual_analysis"]
        assert "preset" in result["grade_applied"]
        assert "strength" in result["grade_applied"]
        assert "description" in result["grade_applied"]
        assert "steps" in result
        assert len(result["steps"]) >= 3
