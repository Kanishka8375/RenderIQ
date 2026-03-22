"""Tests for the color analysis module."""

import numpy as np
import pytest

from renderiq.analyzer import analyze_color_profile, compare_profiles


class TestAnalyzeColorProfile:
    def test_basic_profile(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)

        # Check structure
        assert "rgb" in profile
        assert "hsv" in profile
        assert "lab" in profile
        assert "dominant_colors" in profile
        assert "frame_count" in profile
        assert "metadata" in profile

        assert profile["frame_count"] == len(sample_keyframes)

    def test_histograms_exist(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)

        for space, channels in [
            ("rgb", ["R", "G", "B"]),
            ("hsv", ["H", "S", "V"]),
            ("lab", ["L", "A", "B"]),
        ]:
            for ch in channels:
                hist = profile[space]["histograms"][ch]
                assert len(hist) == 256
                # Normalized histogram should sum to ~1.0
                assert abs(sum(hist) - 1.0) < 0.01

    def test_stats_exist(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)

        for space in ["rgb", "hsv", "lab"]:
            stats = profile[space]["stats"]
            for ch in stats:
                assert "mean" in stats[ch]
                assert "median" in stats[ch]
                assert "std" in stats[ch]
                assert "percentiles" in stats[ch]
                for p in ["p1", "p5", "p25", "p50", "p75", "p95", "p99"]:
                    assert p in stats[ch]["percentiles"]

    def test_dominant_colors(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)
        colors = profile["dominant_colors"]
        assert len(colors) == 8
        for c in colors:
            assert len(c) == 3

    def test_warm_video_has_warm_profile(self, warm_video):
        """Warm video should have high R, low B in mean RGB."""
        from renderiq.sampler import extract_keyframes
        kf = extract_keyframes(warm_video, interval_seconds=1.0)
        profile = analyze_color_profile(kf)
        r_mean = profile["rgb"]["stats"]["R"]["mean"]
        b_mean = profile["rgb"]["stats"]["B"]["mean"]
        assert r_mean > b_mean  # Warm = more red than blue

    def test_cool_video_has_cool_profile(self, cool_video):
        """Cool video should have high B, low R in mean RGB."""
        from renderiq.sampler import extract_keyframes
        kf = extract_keyframes(cool_video, interval_seconds=1.0)
        profile = analyze_color_profile(kf)
        r_mean = profile["rgb"]["stats"]["R"]["mean"]
        b_mean = profile["rgb"]["stats"]["B"]["mean"]
        assert b_mean > r_mean  # Cool = more blue than red

    def test_empty_keyframes_raises(self):
        with pytest.raises(ValueError, match="No keyframes"):
            analyze_color_profile([])


class TestCompareProfiles:
    def test_compare_warm_vs_cool(self, warm_video, cool_video):
        from renderiq.sampler import extract_keyframes
        warm_kf = extract_keyframes(warm_video, interval_seconds=1.0)
        cool_kf = extract_keyframes(cool_video, interval_seconds=1.0)
        warm_profile = analyze_color_profile(warm_kf)
        cool_profile = analyze_color_profile(cool_kf)

        delta = compare_profiles(warm_profile, cool_profile)
        assert "rgb" in delta
        assert "lab" in delta
        # Red should decrease (going warm -> cool)
        assert delta["rgb"]["R"]["mean"] < 0
        # Blue should increase
        assert delta["rgb"]["B"]["mean"] > 0

    def test_identical_profiles_zero_delta(self, sample_keyframes):
        profile = analyze_color_profile(sample_keyframes)
        delta = compare_profiles(profile, profile)
        for space in ["rgb", "hsv", "lab"]:
            for ch in delta[space]:
                assert abs(delta[space][ch]["mean"]) < 0.01
