"""3D LUT generation and .cube file export/import.

Generates a 3D lookup table by histogram matching between source and
reference color profiles in LAB color space, then exports to the
industry-standard .cube format.
"""

import logging
import os

import cv2
import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

logger = logging.getLogger(__name__)


def generate_lut(
    source_profile: dict,
    reference_profile: dict,
    size: int = 33,
) -> np.ndarray:
    """Generate a 3D LUT that maps source colors toward reference colors.

    Uses histogram matching in LAB color space with interpolated CDF
    matching and Gaussian-smoothed transfer curves for perceptually
    accurate, artifact-free results. The entire LUT grid is processed
    in a single vectorized pass for speed.

    Args:
        source_profile: Color profile from analyzer.analyze_color_profile.
        reference_profile: Color profile from analyzer.analyze_color_profile.
        size: LUT grid size per axis (default 33 -> 33^3 entries).

    Returns:
        3D numpy array of shape (size, size, size, 3) with float32 values
        in range [0.0, 1.0] representing the output RGB color for each
        input RGB grid point.
    """
    # Build per-channel transfer functions in LAB space
    lab_mappings = {}
    for channel in ["L", "A", "B"]:
        src_hist = np.array(source_profile["lab"]["histograms"][channel])
        ref_hist = np.array(reference_profile["lab"]["histograms"][channel])
        lab_mappings[channel] = _histogram_match_mapping(src_hist, ref_hist)

    # Build the 3D LUT — vectorized over the full grid
    grid = np.linspace(0, 1, size, dtype=np.float32)
    rr, gg, bb = np.meshgrid(grid, grid, grid, indexing="ij")

    # Shape (size^3, 3) RGB pixels in [0, 1]
    rgb_flat = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], axis=-1)

    # Convert RGB [0,1] -> BGR [0,1] -> LAB via float32 path
    # OpenCV float32: input BGR in [0,1], output L in [0,100], a/b in [-127,127]
    bgr_batch = rgb_flat[:, ::-1].reshape(-1, 1, 3).astype(np.float32)
    lab_batch = cv2.cvtColor(bgr_batch, cv2.COLOR_BGR2Lab)
    lab_flat = lab_batch.reshape(-1, 3)

    # Our histograms were built from uint8 LAB: L in [0,255], a in [0,255], b in [0,255]
    # Convert float32 LAB -> uint8 LAB scale for the transfer functions
    l_vals = lab_flat[:, 0] * (255.0 / 100.0)
    a_vals = lab_flat[:, 1] + 128.0
    b_vals = lab_flat[:, 2] + 128.0

    # Apply transfer functions (output is in uint8-scale LAB)
    l_mapped = np.clip(lab_mappings["L"](l_vals), 0, 255)
    a_mapped = np.clip(lab_mappings["A"](a_vals), 0, 255)
    b_mapped = np.clip(lab_mappings["B"](b_vals), 0, 255)

    # Convert uint8-scale LAB back to float32-scale LAB for OpenCV
    lab_out_float = np.stack([
        l_mapped * (100.0 / 255.0),
        a_mapped - 128.0,
        b_mapped - 128.0,
    ], axis=-1).astype(np.float32).reshape(-1, 1, 3)

    # Convert LAB -> BGR -> RGB in one batch (float32 preserves full precision)
    bgr_out = cv2.cvtColor(lab_out_float, cv2.COLOR_Lab2BGR)
    rgb_out = bgr_out.reshape(-1, 3)[:, ::-1]  # BGR [0,1] -> RGB [0,1]

    lut = np.clip(rgb_out, 0.0, 1.0).reshape(size, size, size, 3).astype(np.float32)

    logger.info("Generated %dx%dx%d LUT (%d entries)", size, size, size, size**3)
    return lut


def generate_lut_from_curves(
    l_curve: np.ndarray,
    a_curve: np.ndarray,
    b_curve: np.ndarray,
    size: int = 33,
) -> np.ndarray:
    """Generate a 3D LUT from explicit LAB channel curves.

    Each curve is a 256-element array mapping input values (0-255) to
    output values (0-255) for that LAB channel.

    Args:
        l_curve: L channel transfer curve (256 values).
        a_curve: A channel transfer curve (256 values).
        b_curve: B channel transfer curve (256 values).
        size: LUT grid size per axis.

    Returns:
        3D LUT array of shape (size, size, size, 3), float32, [0.0, 1.0].
    """
    x = np.arange(256, dtype=np.float64)
    l_fn = interp1d(x, l_curve, kind="linear", bounds_error=False,
                    fill_value=(l_curve[0], l_curve[-1]))
    a_fn = interp1d(x, a_curve, kind="linear", bounds_error=False,
                    fill_value=(a_curve[0], a_curve[-1]))
    b_fn = interp1d(x, b_curve, kind="linear", bounds_error=False,
                    fill_value=(b_curve[0], b_curve[-1]))

    grid = np.linspace(0, 1, size, dtype=np.float32)
    rr, gg, bb = np.meshgrid(grid, grid, grid, indexing="ij")

    rgb_flat = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], axis=-1)
    bgr_batch = rgb_flat[:, ::-1].reshape(-1, 1, 3).astype(np.float32)
    lab_batch = cv2.cvtColor(bgr_batch, cv2.COLOR_BGR2Lab)
    lab_flat = lab_batch.reshape(-1, 3)

    l_vals = lab_flat[:, 0] * (255.0 / 100.0)
    a_vals = lab_flat[:, 1] + 128.0
    b_vals = lab_flat[:, 2] + 128.0

    l_mapped = np.clip(l_fn(l_vals), 0, 255)
    a_mapped = np.clip(a_fn(a_vals), 0, 255)
    b_mapped = np.clip(b_fn(b_vals), 0, 255)

    lab_out_float = np.stack([
        l_mapped * (100.0 / 255.0),
        a_mapped - 128.0,
        b_mapped - 128.0,
    ], axis=-1).astype(np.float32).reshape(-1, 1, 3)

    bgr_out = cv2.cvtColor(lab_out_float, cv2.COLOR_Lab2BGR)
    rgb_out = bgr_out.reshape(-1, 3)[:, ::-1]

    lut = np.clip(rgb_out, 0.0, 1.0).reshape(size, size, size, 3).astype(np.float32)
    return lut


def export_cube(
    lut: np.ndarray,
    output_path: str,
    title: str = "RenderIQ Generated LUT",
) -> str:
    """Export a 3D LUT to .cube file format.

    Args:
        lut: 3D array of shape (size, size, size, 3), values 0.0-1.0.
        output_path: Destination file path for the .cube file.
        title: Title metadata for the .cube file.

    Returns:
        The output file path.
    """
    size = lut.shape[0]
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w") as f:
        f.write(f'TITLE "{title}"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        f.write("\n")

        # .cube ordering: B changes fastest, then G, then R
        for ri in range(size):
            for gi in range(size):
                for bi in range(size):
                    r, g, b = lut[ri, gi, bi]
                    f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")

    logger.info("Exported LUT to %s", output_path)
    return output_path


def load_cube(cube_path: str) -> np.ndarray:
    """Load a .cube LUT file into a numpy array.

    Args:
        cube_path: Path to the .cube file.

    Returns:
        3D numpy array of shape (size, size, size, 3), float32 values 0.0-1.0.
    """
    if not os.path.isfile(cube_path):
        raise FileNotFoundError(f"Cube file not found: {cube_path}")

    size = None
    values = []

    with open(cube_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("TITLE") or \
               line.startswith("DOMAIN"):
                continue
            if line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[-1])
                continue
            parts = line.split()
            if len(parts) == 3:
                try:
                    values.append([float(x) for x in parts])
                except ValueError:
                    continue

    if size is None:
        raise ValueError(f"No LUT_3D_SIZE found in {cube_path}")

    expected = size ** 3
    if len(values) != expected:
        raise ValueError(
            f"Expected {expected} LUT entries, got {len(values)} in {cube_path}"
        )

    # Reconstruct array: .cube ordering is B fastest, G, R slowest
    lut = np.array(values, dtype=np.float32).reshape(size, size, size, 3)
    logger.info("Loaded %dx%dx%d LUT from %s", size, size, size, cube_path)
    return lut


def _histogram_match_mapping(
    src_hist: np.ndarray, ref_hist: np.ndarray
) -> interp1d:
    """Build a transfer function that maps source histogram to reference.

    Uses interpolated CDF matching with Gaussian smoothing for accurate,
    artifact-free color transfer. For each source intensity, finds the
    exact (sub-bin interpolated) reference intensity that matches its
    cumulative distribution position.
    """
    # Compute CDFs
    src_cdf = np.cumsum(src_hist).astype(np.float64)
    src_cdf /= src_cdf[-1] + 1e-10

    ref_cdf = np.cumsum(ref_hist).astype(np.float64)
    ref_cdf /= ref_cdf[-1] + 1e-10

    # Build mapping with sub-bin interpolation for precision
    ref_x = np.arange(256, dtype=np.float64)
    mapping = np.zeros(256, dtype=np.float64)

    for src_val in range(256):
        target_cdf = src_cdf[src_val]

        # Find bracketing indices in reference CDF
        idx = np.searchsorted(ref_cdf, target_cdf)

        if idx <= 0:
            mapping[src_val] = 0.0
        elif idx >= 255:
            mapping[src_val] = 255.0
        else:
            # Linear interpolation between ref bins for sub-bin precision
            low = ref_cdf[idx - 1]
            high = ref_cdf[idx]
            denom = high - low
            if denom > 1e-12:
                frac = (target_cdf - low) / denom
                mapping[src_val] = (idx - 1) + frac
            else:
                mapping[src_val] = float(idx)

    # Gaussian smooth the transfer curve to prevent harsh jumps / banding
    # sigma=1.5 is gentle enough to preserve detail but removes noise
    mapping = gaussian_filter1d(mapping, sigma=1.5)
    mapping = np.clip(mapping, 0, 255)

    # Ensure monotonicity (a non-monotonic curve creates color inversions)
    for i in range(1, 256):
        if mapping[i] < mapping[i - 1]:
            mapping[i] = mapping[i - 1]

    # Create interpolation function for continuous input values
    x = np.arange(256, dtype=np.float64)
    return interp1d(
        x, mapping, kind="cubic", bounds_error=False,
        fill_value=(mapping[0], mapping[-1])
    )
