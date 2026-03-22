"""Apply a 3D LUT to raw video footage frame by frame.

Uses FFmpeg for decoding/encoding and trilinear interpolation for
accurate color mapping between LUT grid points.
"""

import logging
import os
import subprocess

import cv2
import numpy as np
from tqdm import tqdm

from renderiq.lut_generator import load_cube
from renderiq.utils import get_video_info

logger = logging.getLogger(__name__)


def apply_lut_to_frame(frame: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Apply 3D LUT to a single frame using trilinear interpolation.

    Args:
        frame: (H, W, 3) uint8 RGB image.
        lut: (size, size, size, 3) float32 LUT, values 0.0-1.0.

    Returns:
        (H, W, 3) uint8 RGB graded image.
    """
    size = lut.shape[0]
    h, w, _ = frame.shape

    # Normalize to 0-1 and scale to LUT indices
    pixels = frame.astype(np.float32) / 255.0
    scaled = pixels * (size - 1)

    # Get integer indices and fractional parts
    lower = np.floor(scaled).astype(np.int32)
    upper = np.minimum(lower + 1, size - 1)
    frac = scaled - lower.astype(np.float32)

    # Flatten for indexing
    r0, g0, b0 = lower[:, :, 0], lower[:, :, 1], lower[:, :, 2]
    r1, g1, b1 = upper[:, :, 0], upper[:, :, 1], upper[:, :, 2]
    fr, fg, fb = frac[:, :, 0], frac[:, :, 1], frac[:, :, 2]

    # Trilinear interpolation
    # Interpolate along B axis
    c00 = lut[r0, g0, b0] * (1 - fb[..., None]) + lut[r0, g0, b1] * fb[..., None]
    c01 = lut[r0, g1, b0] * (1 - fb[..., None]) + lut[r0, g1, b1] * fb[..., None]
    c10 = lut[r1, g0, b0] * (1 - fb[..., None]) + lut[r1, g0, b1] * fb[..., None]
    c11 = lut[r1, g1, b0] * (1 - fb[..., None]) + lut[r1, g1, b1] * fb[..., None]

    # Interpolate along G axis
    c0 = c00 * (1 - fg[..., None]) + c01 * fg[..., None]
    c1 = c10 * (1 - fg[..., None]) + c11 * fg[..., None]

    # Interpolate along R axis
    result = c0 * (1 - fr[..., None]) + c1 * fr[..., None]

    # Convert back to uint8
    result = np.clip(result * 255, 0, 255).astype(np.uint8)
    return result


def apply_lut_to_video(
    video_path: str,
    lut: np.ndarray,
    output_path: str,
    quality: int = 18,
) -> str:
    """Apply LUT to every frame of a video.

    Processes frame by frame to avoid loading entire video into memory.
    Preserves original audio track without re-encoding.

    Args:
        video_path: Path to the raw footage.
        lut: 3D LUT array (size, size, size, 3) or path to .cube file.
        output_path: Destination path for graded video.
        quality: CRF value for H.264 encoding (lower = better, default 18).

    Returns:
        Output file path.
    """
    if isinstance(lut, str):
        lut = load_cube(lut)

    info = get_video_info(video_path)
    total_frames = int(info["duration"] * info["fps"])
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    # Write graded frames to a temp file without audio first
    temp_video = output_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        temp_video, fourcc, info["fps"],
        (info["width"], info["height"])
    )

    if not writer.isOpened():
        cap.release()
        raise IOError(f"Cannot create output video: {temp_video}")

    logger.info(
        "Grading %d frames (%dx%d @ %.1f fps)",
        total_frames, info["width"], info["height"], info["fps"],
    )

    with tqdm(total=total_frames, desc="Grading", unit="frame") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # BGR -> RGB -> grade -> RGB -> BGR
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            graded = apply_lut_to_frame(rgb, lut)
            bgr = cv2.cvtColor(graded, cv2.COLOR_RGB2BGR)
            writer.write(bgr)
            pbar.update(1)

    cap.release()
    writer.release()

    # Mux with original audio using FFmpeg
    if info["has_audio"]:
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", video_path,
            "-c:v", "libx264", "-crf", str(quality),
            "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-map", "0:v:0", "-map", "1:a?",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-c:v", "libx264", "-crf", str(quality),
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    subprocess.run(cmd, capture_output=True, check=True)
    os.remove(temp_video)
    logger.info("Graded video saved to %s", output_path)
    return output_path


def preview_grade(
    video_path: str,
    lut: np.ndarray,
    timestamp: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (original_frame, graded_frame) for quick visual comparison.

    Args:
        video_path: Path to the video file.
        lut: 3D LUT array.
        timestamp: Time in seconds to extract frame. If None, uses midpoint.

    Returns:
        Tuple of (original RGB frame, graded RGB frame).
    """
    if isinstance(lut, str):
        lut = load_cube(lut)

    info = get_video_info(video_path)
    if timestamp is None:
        timestamp = info["duration"] / 2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    frame_idx = int(timestamp * info["fps"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError(f"Could not read frame at timestamp {timestamp}s")

    original = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    graded = apply_lut_to_frame(original, lut)
    return original, graded
