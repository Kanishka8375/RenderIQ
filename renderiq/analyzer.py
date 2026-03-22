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

OVEREXPOSED_THRESHOLD = 240
UNDEREXPOSED_THRESHOLD = 15
EXPOSURE_PIXEL_RATIO = 0.30
NORMAL_WEIGHT = 1.0
ABNORMAL_WEIGHT = 0.3


def analyze_color_profile(keyframes: list[dict]) -> dict:
    """Analyze color distribution across keyframes.

    Args:
        keyframes: List of dicts with "frame" key containing RGB np.ndarray.

    Returns:
        Color profile dict with histograms, stats, dominant colors,
        and exposure warnings for RGB, HSV, and LAB color spaces.
    """
    if not keyframes:
        raise ValueError("No keyframes provided for analysis")

    rgb_frames = [kf["frame"] for kf in keyframes]
    frame_count = len(rgb_frames)

    # 1.3: Detect exposure issues and compute per-frame weights
    weights = []
    overexposed_count = 0
    underexposed_count = 0

    for f in rgb_frames:
        overexposed = _is_overexposed(f)
        underexposed = _is_underexposed(f)
        if overexposed:
            overexposed_count += 1
        if underexposed:
            underexposed_count += 1
        if overexposed or underexposed:
            weights.append(ABNORMAL_WEIGHT)
        else:
            weights.append(NORMAL_WEIGHT)

    # Convert to other color spaces
    hsv_frames = [cv2.cvtColor(f, cv2.COLOR_RGB2HSV) for f in rgb_frames]
    lab_frames = [cv2.cvtColor(f, cv2.COLOR_RGB2LAB) for f in rgb_frames]

    logger.info("Analyzing %d frames across 3 color spaces", frame_count)

    profile = {
        "rgb": _analyze_space(rgb_frames, ["R", "G", "B"], weights),
        "hsv": _analyze_space(hsv_frames, ["H", "S", "V"], weights),
        "lab": _analyze_space(lab_frames, ["L", "A", "B"], weights),
        "dominant_colors": _find_dominant_colors(lab_frames, n_colors=8),
        "frame_count": frame_count,
        "metadata": {
            "avg_brightness": _avg_brightness(lab_frames),
            "avg_saturation": _avg_saturation(hsv_frames),
        },
        "warnings": {
            "overexposed_frames": overexposed_count,
            "underexposed_frames": underexposed_count,
            "total_frames": frame_count,
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


def cluster_keyframes(keyframes: list[dict], n_clusters: int = 3) -> list[list[dict]]:
    """Cluster keyframes by visual similarity using K-means on LAB histograms.

    Args:
        keyframes: List of keyframe dicts with "frame" key.
        n_clusters: Number of clusters (default 3).

    Returns:
        List of lists, where each inner list contains keyframes for one cluster.
    """
    if len(keyframes) <= n_clusters:
        return [[kf] for kf in keyframes]

    # Build feature vectors from LAB histograms
    features = []
    for kf in keyframes:
        lab = cv2.cvtColor(kf["frame"], cv2.COLOR_RGB2LAB)
        hist_l = cv2.calcHist([lab], [0], None, [32], [0, 256]).flatten()
        hist_a = cv2.calcHist([lab], [1], None, [32], [0, 256]).flatten()
        hist_b = cv2.calcHist([lab], [2], None, [32], [0, 256]).flatten()
        # Normalize
        hist_l = hist_l / (hist_l.sum() + 1e-10)
        hist_a = hist_a / (hist_a.sum() + 1e-10)
        hist_b = hist_b / (hist_b.sum() + 1e-10)
        features.append(np.concatenate([hist_l, hist_a, hist_b]))

    features = np.array(features, dtype=np.float32)

    # Adjust k if fewer unique clusters exist
    actual_k = min(n_clusters, len(keyframes))
    kmeans = MiniBatchKMeans(n_clusters=actual_k, random_state=42, n_init=3)
    labels = kmeans.fit_predict(features)

    clusters = [[] for _ in range(actual_k)]
    for i, label in enumerate(labels):
        clusters[label].append(keyframes[i])

    # Remove empty clusters
    clusters = [c for c in clusters if c]
    return clusters


def classify_frame(frame: np.ndarray, cluster_profiles: list[dict]) -> int:
    """Determine which cluster a frame is closest to.

    Args:
        frame: RGB numpy array.
        cluster_profiles: List of color profiles, one per cluster.

    Returns:
        Index of the closest cluster.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
    frame_l_mean = lab[:, :, 0].mean()
    frame_a_mean = lab[:, :, 1].mean()
    frame_b_mean = lab[:, :, 2].mean()

    best_idx = 0
    best_dist = float("inf")

    for i, profile in enumerate(cluster_profiles):
        stats = profile["lab"]["stats"]
        l_mean = stats["L"]["mean"]
        a_mean = stats["A"]["mean"]
        b_mean = stats["B"]["mean"]
        dist = (
            (frame_l_mean - l_mean) ** 2
            + (frame_a_mean - a_mean) ** 2
            + (frame_b_mean - b_mean) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best_idx = i

    return best_idx


def _is_overexposed(frame: np.ndarray) -> bool:
    """Check if frame is overexposed (>30% pixels have value >240 in any channel)."""
    for c in range(3):
        ratio = (frame[:, :, c] > OVEREXPOSED_THRESHOLD).mean()
        if ratio > EXPOSURE_PIXEL_RATIO:
            return True
    return False


def _is_underexposed(frame: np.ndarray) -> bool:
    """Check if frame is underexposed (>30% pixels have value <15 in any channel)."""
    for c in range(3):
        ratio = (frame[:, :, c] < UNDEREXPOSED_THRESHOLD).mean()
        if ratio > EXPOSURE_PIXEL_RATIO:
            return True
    return False


def _analyze_space(
    frames: list[np.ndarray], channel_names: list[str],
    weights: list[float] | None = None,
) -> dict:
    """Compute histograms and statistics for a set of frames in one color space."""
    if weights is None:
        weights = [1.0] * len(frames)

    # Build weighted pixel array by repeating pixels based on weight
    # For efficiency, we sample proportionally instead of repeating
    weighted_pixels = []
    for f, w in zip(frames, weights):
        pixels = f.reshape(-1, 3)
        if w < 1.0:
            # Subsample to simulate lower weight
            n_keep = max(1, int(len(pixels) * w))
            rng = np.random.default_rng(42)
            indices = rng.choice(len(pixels), n_keep, replace=False)
            weighted_pixels.append(pixels[indices])
        else:
            weighted_pixels.append(pixels)

    all_pixels = np.concatenate(weighted_pixels, axis=0)

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
