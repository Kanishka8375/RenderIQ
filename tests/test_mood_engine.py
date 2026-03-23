"""Tests for smart_grade.mood_engine module."""

import pytest

from renderiq.smart_grade.mood_engine import (
    compute_mood_profile,
    _map_mood_to_preset,
    _generate_description,
)


@pytest.fixture
def epic_audio():
    return {
        "primary_mood": "epic",
        "secondary_mood": "dramatic",
        "intensity": 0.8,
        "warmth": 0.7,
        "complexity": 0.6,
        "mood_tags": ["epic", "powerful"],
    }


@pytest.fixture
def calm_audio():
    return {
        "primary_mood": "calm",
        "secondary_mood": "steady",
        "intensity": 0.2,
        "warmth": 0.4,
        "complexity": 0.2,
        "mood_tags": ["calm", "peaceful"],
    }


@pytest.fixture
def outdoor_visual():
    return {
        "scene_type": "outdoor_warm",
        "brightness": 0.65,
        "saturation_level": 0.5,
        "contrast_level": 0.5,
        "warmth": 0.6,
        "has_faces": False,
        "motion_level": 0.3,
        "visual_tags": ["bright", "warm"],
    }


@pytest.fixture
def portrait_visual():
    return {
        "scene_type": "portrait",
        "brightness": 0.5,
        "saturation_level": 0.4,
        "contrast_level": 0.4,
        "warmth": 0.5,
        "has_faces": True,
        "motion_level": 0.1,
        "visual_tags": ["people"],
    }


class TestComputeMoodProfile:
    def test_returns_all_required_fields(self, epic_audio, outdoor_visual):
        profile = compute_mood_profile(epic_audio, outdoor_visual)
        required = [
            "mood", "target_brightness", "target_saturation", "target_contrast",
            "target_warmth", "shadow_color", "highlight_color",
            "recommended_preset", "recommended_strength", "grade_description",
            "confidence", "audio_mood", "visual_scene", "has_faces", "mood_tags",
        ]
        for field in required:
            assert field in profile, f"Missing field: {field}"

    def test_target_values_in_range(self, epic_audio, outdoor_visual):
        profile = compute_mood_profile(epic_audio, outdoor_visual)
        assert 0 <= profile["target_brightness"] <= 1
        assert 0 <= profile["target_saturation"] <= 1
        assert 0 <= profile["target_contrast"] <= 1
        assert 0 <= profile["target_warmth"] <= 1
        assert 0.2 <= profile["recommended_strength"] <= 0.9

    def test_epic_mood_gets_cinematic_or_teal(self, epic_audio, outdoor_visual):
        profile = compute_mood_profile(epic_audio, outdoor_visual)
        assert profile["recommended_preset"] in ("cinematic_warm", "teal_orange")

    def test_calm_mood_gets_soft_or_cold(self, calm_audio, outdoor_visual):
        profile = compute_mood_profile(calm_audio, outdoor_visual)
        assert profile["recommended_preset"] in ("pastel_soft", "cinematic_cold")

    def test_face_detection_caps_saturation(self, epic_audio, portrait_visual):
        profile = compute_mood_profile(epic_audio, portrait_visual)
        assert profile["target_saturation"] <= 0.6
        assert profile["has_faces"] is True

    def test_face_detection_reduces_strength(self, epic_audio, portrait_visual):
        no_face = portrait_visual.copy()
        no_face["has_faces"] = False
        profile_face = compute_mood_profile(epic_audio, portrait_visual)
        profile_no_face = compute_mood_profile(epic_audio, no_face)
        assert profile_face["recommended_strength"] < profile_no_face["recommended_strength"]

    def test_confidence_higher_with_audio_signal(self, epic_audio, calm_audio, outdoor_visual):
        profile_epic = compute_mood_profile(epic_audio, outdoor_visual)
        neutral_audio = {
            "primary_mood": "neutral",
            "intensity": 0.2,
            "warmth": 0.5,
            "mood_tags": [],
        }
        profile_neutral = compute_mood_profile(neutral_audio, outdoor_visual)
        assert profile_epic["confidence"] > profile_neutral["confidence"]

    def test_mood_tags_combined(self, epic_audio, outdoor_visual):
        profile = compute_mood_profile(epic_audio, outdoor_visual)
        # Should contain tags from both audio and visual
        assert len(profile["mood_tags"]) > 0


class TestMapMoodToPreset:
    def test_all_moods_return_valid_preset(self):
        moods = ["epic", "intense", "upbeat", "dark", "warm", "melancholic", "calm", "neutral"]
        for mood in moods:
            for w in [True, False]:
                for i in [True, False]:
                    preset, strength = _map_mood_to_preset(mood, 0.6 if w else 0.3, 0.6 if i else 0.3, 0.5, False)
                    assert isinstance(preset, str)
                    assert 0.2 <= strength <= 0.9

    def test_dark_footage_reduces_moody_strength(self):
        preset, strength_normal = _map_mood_to_preset("dark", 0.3, 0.6, 0.5, False)
        preset2, strength_dark = _map_mood_to_preset("dark", 0.3, 0.6, 0.15, False)
        if preset == "moody_dark" and preset2 == "moody_dark":
            assert strength_dark < strength_normal


class TestGenerateDescription:
    def test_returns_string(self):
        desc = _generate_description("epic", 0.7, 0.8, "cinematic_warm")
        assert isinstance(desc, str)
        assert len(desc) > 10

    def test_includes_intensity_word(self):
        desc = _generate_description("epic", 0.7, 0.8, "cinematic_warm")
        assert any(w in desc for w in ["Dramatic", "Moderate", "Subtle"])

    def test_includes_warmth_word(self):
        desc = _generate_description("epic", 0.7, 0.8, "cinematic_warm")
        assert any(w in desc for w in ["warm", "cool", "balanced"])
