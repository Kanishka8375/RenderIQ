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

logger = logging.getLogger(__name__)


def generate_lut(
    source_profile: dict,
    reference_profile: dict,
    size: int = 33,
) -> np.ndarray:
    """Generate a 3D LUT that maps source colors toward reference colors.

    Uses histogram matching in LAB color space for perceptually
    accurate results.

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

    # Build the 3D LUT
    lut = np.zeros((size, size, size, 3), dtype=np.float32)

    # Create grid of input RGB values
    grid = np.linspace(0, 1, size, dtype=np.float32)

    for ri, r in enumerate(grid):
        for gi, g in enumerate(grid):
            for bi, b in enumerate(grid):
                # Convert input RGB (0-1) to BGR uint8 for OpenCV
                rgb_pixel = np.array([[[r, g, b]]], dtype=np.float32) * 255.0
                bgr_pixel = rgb_pixel[:, :, ::-1].astype(np.uint8)

                # Convert to LAB
                lab_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2LAB)
                l_val = float(lab_pixel[0, 0, 0])
                a_val = float(lab_pixel[0, 0, 1])
                b_val = float(lab_pixel[0, 0, 2])

                # Apply histogram matching in LAB
                l_mapped = lab_mappings["L"](l_val)
                a_mapped = lab_mappings["A"](a_val)
                b_mapped = lab_mappings["B"](b_val)

                # Clamp to valid LAB ranges
                l_mapped = np.clip(l_mapped, 0, 255)
                a_mapped = np.clip(a_mapped, 0, 255)
                b_mapped = np.clip(b_mapped, 0, 255)

                # Convert back to RGB
                lab_out = np.array(
                    [[[l_mapped, a_mapped, b_mapped]]], dtype=np.uint8
                )
                bgr_out = cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)
                rgb_out = bgr_out[0, 0, ::-1].astype(np.float32) / 255.0

                lut[ri, gi, bi] = np.clip(rgb_out, 0.0, 1.0)

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
    # Build interpolation functions
    x = np.arange(256, dtype=np.float64)
    l_fn = interp1d(x, l_curve, kind="linear", bounds_error=False,
                    fill_value=(l_curve[0], l_curve[-1]))
    a_fn = interp1d(x, a_curve, kind="linear", bounds_error=False,
                    fill_value=(a_curve[0], a_curve[-1]))
    b_fn = interp1d(x, b_curve, kind="linear", bounds_error=False,
                    fill_value=(b_curve[0], b_curve[-1]))

    lut = np.zeros((size, size, size, 3), dtype=np.float32)
    grid = np.linspace(0, 1, size, dtype=np.float32)

    for ri, r in enumerate(grid):
        for gi, g in enumerate(grid):
            for bi, b in enumerate(grid):
                rgb_pixel = np.array([[[r, g, b]]], dtype=np.float32) * 255.0
                bgr_pixel = rgb_pixel[:, :, ::-1].astype(np.uint8)
                lab_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2LAB)

                l_val = float(lab_pixel[0, 0, 0])
                a_val = float(lab_pixel[0, 0, 1])
                b_val = float(lab_pixel[0, 0, 2])

                l_out = np.clip(l_fn(l_val), 0, 255)
                a_out = np.clip(a_fn(a_val), 0, 255)
                b_out = np.clip(b_fn(b_val), 0, 255)

                lab_out = np.array([[[l_out, a_out, b_out]]], dtype=np.uint8)
                bgr_out = cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)
                rgb_out = bgr_out[0, 0, ::-1].astype(np.float32) / 255.0
                lut[ri, gi, bi] = np.clip(rgb_out, 0.0, 1.0)

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

    Uses CDF matching: for each source intensity, find the reference
    intensity with the same cumulative distribution position.
    """
    # Compute CDFs
    src_cdf = np.cumsum(src_hist)
    src_cdf = src_cdf / (src_cdf[-1] + 1e-10)

    ref_cdf = np.cumsum(ref_hist)
    ref_cdf = ref_cdf / (ref_cdf[-1] + 1e-10)

    # For each source bin, find the reference bin with closest CDF value
    mapping = np.zeros(256, dtype=np.float64)
    for src_val in range(256):
        # Find reference value where ref_cdf is closest to src_cdf[src_val]
        idx = np.searchsorted(ref_cdf, src_cdf[src_val])
        mapping[src_val] = min(idx, 255)

    # Create interpolation function for continuous input values
    x = np.arange(256, dtype=np.float64)
    return interp1d(
        x, mapping, kind="linear", bounds_error=False,
        fill_value=(mapping[0], mapping[-1])
    )
