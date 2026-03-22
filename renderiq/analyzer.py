"""Color distribution analysis for video keyframes.

Analyzes color histograms and statistics across RGB, HSV, and LAB
color spaces, and identifies dominant colors via K-means clustering.
"""

import logging

import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans

logger = logging.getLogger(__name__)

PERCENTILES = [1, 5, 25, 50, 75, 95, 99]


def analyze_color_profile(keyframes: list[dict]) -> dict:
    """Analyze color distribution across keyframes.

    Args:
        keyframes: List of dicts with "frame" key containing RGB np.ndarray.

    Returns:
        Color profile dict with histograms, stats, and dominant colors
        for RGB, HSV, and LAB color spaces.
    """
    if not keyframes:
        raise ValueError("No keyframes provided for analysis")

    rgb_frames = [kf["frame"] for kf in keyframes]
    frame_count = len(rgb_frames)

    # Convert to other color spaces
    hsv_frames = [cv2.cvtColor(f, cv2.COLOR_RGB2HSV) for f in rgb_frames]
    lab_frames = [cv2.cvtColor(f, cv2.COLOR_RGB2LAB) for f in rgb_frames]

    logger.info("Analyzing %d frames across 3 color spaces", frame_count)

    profile = {
        "rgb": _analyze_space(rgb_frames, ["R", "G", "B"]),
        "hsv": _analyze_space(hsv_frames, ["H", "S", "V"]),
        "lab": _analyze_space(lab_frames, ["L", "A", "B"]),
        "dominant_colors": _find_dominant_colors(lab_frames, n_colors=8),
        "frame_count": frame_count,
        "metadata": {
            "avg_brightness": _avg_brightness(lab_frames),
            "avg_saturation": _avg_saturation(hsv_frames),
        },
    }

    return profile


def compare_profiles(source_profile: dict, reference_profile: dict) -> dict:
    """Compare two color profiles and return the delta/difference.

    This tells us HOW MUCH we need to shift the source to match the reference.

    Args:
        source_profile: Color profile of the source footage.
        reference_profile: Color profile of the reference footage.

    Returns:
        Dict containing per-channel deltas for each color space.
    """
    delta = {}
    for space in ["rgb", "hsv", "lab"]:
        src_stats = source_profile[space]["stats"]
        ref_stats = reference_profile[space]["stats"]
        space_delta = {}
        for channel in src_stats:
            ch_delta = {}
            for stat_name in ["mean", "median", "std"]:
                ch_delta[stat_name] = (
                    ref_stats[channel][stat_name] - src_stats[channel][stat_name]
                )
            ch_delta["percentile_deltas"] = {}
            for p in PERCENTILES:
                key = f"p{p}"
                ch_delta["percentile_deltas"][key] = (
                    ref_stats[channel]["percentiles"][key]
                    - src_stats[channel]["percentiles"][key]
                )
            space_delta[channel] = ch_delta
        delta[space] = space_delta

    return delta


def _analyze_space(
    frames: list[np.ndarray], channel_names: list[str]
) -> dict:
    """Compute histograms and statistics for a set of frames in one color space."""
    # Stack all pixel data
    all_pixels = np.concatenate([f.reshape(-1, 3) for f in frames], axis=0)

    histograms = {}
    stats = {}

    for i, name in enumerate(channel_names):
        channel_data = all_pixels[:, i].astype(np.float64)

        # Histogram (256 bins)
        hist, bin_edges = np.histogram(channel_data, bins=256, range=(0, 256))
        hist = hist.astype(np.float64)
        hist /= hist.sum() + 1e-10  # Normalize

        histograms[name] = hist.tolist()

        # Statistics
        percentiles = {}
        for p in PERCENTILES:
            percentiles[f"p{p}"] = float(np.percentile(channel_data, p))

        stats[name] = {
            "mean": float(np.mean(channel_data)),
            "median": float(np.median(channel_data)),
            "std": float(np.std(channel_data)),
            "percentiles": percentiles,
        }

    return {"histograms": histograms, "stats": stats}


def _find_dominant_colors(
    lab_frames: list[np.ndarray], n_colors: int = 8
) -> list[list[float]]:
    """Find dominant colors using K-means clustering in LAB space."""
    # Sample pixels to keep clustering fast
    max_pixels = 100_000
    all_pixels = np.concatenate(
        [f.reshape(-1, 3) for f in lab_frames], axis=0
    ).astype(np.float32)

    if len(all_pixels) > max_pixels:
        indices = np.random.default_rng(42).choice(
            len(all_pixels), max_pixels, replace=False
        )
        all_pixels = all_pixels[indices]

    kmeans = MiniBatchKMeans(n_clusters=n_colors, random_state=42, n_init=3)
    kmeans.fit(all_pixels)

    # Sort by cluster size (most common first)
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    order = np.argsort(-counts)
    centers = kmeans.cluster_centers_[order]

    return centers.tolist()


def _avg_brightness(lab_frames: list[np.ndarray]) -> float:
    """Average L channel value across all frames."""
    total = sum(f[:, :, 0].mean() for f in lab_frames)
    return float(total / len(lab_frames))


def _avg_saturation(hsv_frames: list[np.ndarray]) -> float:
    """Average S channel value across all frames."""
    total = sum(f[:, :, 1].mean() for f in hsv_frames)
    return float(total / len(hsv_frames))
