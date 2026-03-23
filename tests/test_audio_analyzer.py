"""Tests for smart_grade.audio_analyzer module."""

import os
import subprocess
import tempfile

import numpy as np
import pytest


@pytest.fixture
def video_with_audio(tmp_path):
    """Create a test video with a sine-wave audio track."""
    path = str(tmp_path / "audio_test.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#808080:s=320x240:d=3:r=24",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


@pytest.fixture
def video_no_audio(tmp_path):
    """Create a test video with no audio track."""
    path = str(tmp_path / "no_audio.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#808080:s=320x240:d=2:r=24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-an", path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


class TestExtractAudio:
    def test_extract_audio_success(self, video_with_audio, tmp_path):
        from renderiq.smart_grade.audio_analyzer import extract_audio
        wav_path = extract_audio(video_with_audio)
        assert os.path.exists(wav_path)
        assert os.path.getsize(wav_path) > 100
        os.remove(wav_path)

    def test_extract_audio_custom_output(self, video_with_audio, tmp_path):
        from renderiq.smart_grade.audio_analyzer import extract_audio
        out = str(tmp_path / "custom.wav")
        result = extract_audio(video_with_audio, output_path=out)
        assert result == out
        assert os.path.exists(out)

    def test_extract_audio_no_audio_track(self, video_no_audio):
        from renderiq.smart_grade.audio_analyzer import extract_audio
        with pytest.raises(RuntimeError):
            extract_audio(video_no_audio)


class TestAnalyzeMusicFeatures:
    def test_features_from_sine_wave(self, video_with_audio):
        from renderiq.smart_grade.audio_analyzer import extract_audio, analyze_music_features
        wav = extract_audio(video_with_audio)
        try:
            features = analyze_music_features(wav)
            assert features["has_audio"] is True
            assert "tempo" in features
            assert "energy" in features
            assert 0 <= features["energy"] <= 1
            assert "mfcc_means" in features
            assert len(features["mfcc_means"]) == 13
            assert "chroma_energy" in features
            assert isinstance(features["onset_density"], float)
            assert 0 <= features["dynamic_range"] <= 1
        finally:
            os.remove(wav)

    def test_silence_detection(self, tmp_path):
        """A nearly silent audio file should be detected."""
        from renderiq.smart_grade.audio_analyzer import analyze_music_features
        # Create a silent WAV
        path = str(tmp_path / "silence.wav")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=22050",
            "-t", "2", "-c:a", "pcm_s16le", path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        features = analyze_music_features(path)
        assert features["has_audio"] is False


class TestClassifyAudioMood:
    def test_no_audio_returns_neutral(self):
        from renderiq.smart_grade.audio_analyzer import classify_audio_mood
        mood = classify_audio_mood({"has_audio": False})
        assert mood["primary_mood"] == "neutral"
        assert mood["intensity"] == 0.3
        assert "silent" in mood["mood_tags"]

    def test_high_energy_classifies_intense(self):
        from renderiq.smart_grade.audio_analyzer import classify_audio_mood
        features = {
            "has_audio": True,
            "tempo": 160.0,
            "energy": 0.9,
            "spectral_centroid": 5000.0,
            "onset_density": 6.0,
            "dynamic_range": 0.6,
            "has_speech": False,
            "has_music": True,
        }
        mood = classify_audio_mood(features)
        assert mood["primary_mood"] in ("epic", "intense")
        assert mood["intensity"] > 0.5

    def test_low_energy_warm_classifies_warm_or_calm(self):
        from renderiq.smart_grade.audio_analyzer import classify_audio_mood
        features = {
            "has_audio": True,
            "tempo": 70.0,
            "energy": 0.2,
            "spectral_centroid": 2000.0,
            "onset_density": 1.0,
            "dynamic_range": 0.2,
            "has_speech": False,
            "has_music": True,
        }
        mood = classify_audio_mood(features)
        assert mood["primary_mood"] in ("warm", "calm")
        assert mood["warmth"] > 0.4

    def test_mood_returns_all_required_fields(self):
        from renderiq.smart_grade.audio_analyzer import classify_audio_mood
        features = {
            "has_audio": True,
            "tempo": 120.0,
            "energy": 0.5,
            "spectral_centroid": 3000.0,
            "onset_density": 3.0,
            "dynamic_range": 0.3,
            "has_speech": False,
            "has_music": True,
        }
        mood = classify_audio_mood(features)
        assert "primary_mood" in mood
        assert "secondary_mood" in mood
        assert "intensity" in mood
        assert "warmth" in mood
        assert "complexity" in mood
        assert "mood_tags" in mood
        assert 0 <= mood["intensity"] <= 1
        assert 0 <= mood["warmth"] <= 1
        assert 0 <= mood["complexity"] <= 1
