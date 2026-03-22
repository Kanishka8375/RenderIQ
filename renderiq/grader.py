"""Apply a 3D LUT to raw video footage frame by frame.

Uses FFmpeg for decoding/encoding and trilinear interpolation for
accurate color mapping between LUT grid points.
"""

import logging
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import cv2
import numpy as np
from tqdm import tqdm

from renderiq.lut_generator import load_cube
from renderiq.utils import get_video_info, check_gpu_available

logger = logging.getLogger(__name__)


def apply_lut_to_frame(
    frame: np.ndarray,
    lut: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """Apply 3D LUT to a single frame using trilinear interpolation.

    Args:
        frame: (H, W, 3) uint8 RGB image.
        lut: (size, size, size, 3) float32 LUT, values 0.0-1.0.
        strength: Grade intensity 0.0 (no change) to 1.0 (full grade).

    Returns:
        (H, W, 3) uint8 RGB graded image.
    """
    size = lut.shape[0]

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
    graded = c0 * (1 - fr[..., None]) + c1 * fr[..., None]

    # Apply strength blending
    if strength < 1.0:
        graded = pixels * (1.0 - strength) + graded * strength

    # Convert back to uint8
    result = np.clip(graded * 255, 0, 255).astype(np.uint8)
    return result


def auto_white_balance(frame: np.ndarray) -> np.ndarray:
    """Apply auto white balance using the gray world assumption.

    The average color of a scene should be neutral gray. This computes
    correction factors to shift the average toward neutral.

    Args:
        frame: (H, W, 3) uint8 RGB image.

    Returns:
        White-balanced (H, W, 3) uint8 RGB image.
    """
    avg = frame.mean(axis=(0, 1)).astype(np.float64)
    gray_target = avg.mean()

    # Compute per-channel scale factors
    scales = np.where(avg > 0, gray_target / avg, 1.0)

    # Apply correction
    corrected = frame.astype(np.float64) * scales[None, None, :]
    return np.clip(corrected, 0, 255).astype(np.uint8)


def apply_lut_to_video(
    video_path: str,
    lut: np.ndarray,
    output_path: str,
    quality: int = 18,
    strength: float = 1.0,
    auto_wb: bool = False,
    workers: int | None = None,
    use_gpu: bool = False,
) -> str:
    """Apply LUT to every frame of a video.

    Processes frame by frame to avoid loading entire video into memory.
    Preserves original audio track without re-encoding.

    Args:
        video_path: Path to the raw footage.
        lut: 3D LUT array (size, size, size, 3) or path to .cube file.
        output_path: Destination path for graded video.
        quality: CRF value for H.264 encoding (lower = better, default 18).
        strength: Grade intensity 0.0-1.0 (default 1.0).
        auto_wb: Apply auto white balance before grading.
        workers: Number of parallel workers (None = sequential).
        use_gpu: Try to use GPU encoding (h264_nvenc).

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
        if workers and workers > 1:
            _grade_parallel(cap, writer, lut, strength, auto_wb, workers, pbar)
        else:
            _grade_sequential(cap, writer, lut, strength, auto_wb, pbar)

    cap.release()
    writer.release()

    # Determine encoder
    encoder = "libx264"
    encoder_opts = ["-crf", str(quality)]
    if use_gpu and check_gpu_available():
        encoder = "h264_nvenc"
        encoder_opts = ["-preset", "medium", "-qp", str(quality)]

    # Mux with original audio using FFmpeg
    _mux_audio(temp_video, video_path, output_path, info, encoder, encoder_opts)

    if os.path.exists(temp_video):
        os.remove(temp_video)

    logger.info("Graded video saved to %s", output_path)
    return output_path


def _grade_sequential(cap, writer, lut, strength, auto_wb, pbar):
    """Grade frames one at a time."""
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if auto_wb:
            rgb = auto_white_balance(rgb)
        graded = apply_lut_to_frame(rgb, lut, strength=strength)
        bgr = cv2.cvtColor(graded, cv2.COLOR_RGB2BGR)
        writer.write(bgr)
        pbar.update(1)


def _grade_parallel(cap, writer, lut, strength, auto_wb, workers, pbar):
    """Grade frames using parallel workers with batching."""
    batch_size = workers * 4

    while True:
        batch = []
        for _ in range(batch_size):
            ret, frame = cap.read()
            if not ret:
                break
            batch.append(frame)

        if not batch:
            break

        # Process batch in parallel
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for frame in batch:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if auto_wb:
                    rgb = auto_white_balance(rgb)
                futures.append(
                    executor.submit(_grade_single_frame, rgb, lut, strength)
                )
            for future in futures:
                graded = future.result()
                bgr = cv2.cvtColor(graded, cv2.COLOR_RGB2BGR)
                writer.write(bgr)
                pbar.update(1)


def _grade_single_frame(rgb_frame, lut, strength):
    """Grade a single frame (for use in process pool)."""
    return apply_lut_to_frame(rgb_frame, lut, strength=strength)


def _mux_audio(temp_video, original_video, output_path, info, encoder, encoder_opts):
    """Mux graded video with original audio, handling edge cases."""
    base_cmd = [
        "ffmpeg", "-y",
        "-i", temp_video,
    ]

    if info["has_audio"]:
        # Try copying audio first
        cmd = base_cmd + [
            "-i", original_video,
            "-c:v", encoder, *encoder_opts,
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-map", "0:v:0",
        ]
        # Map all audio streams
        for i in range(info.get("audio_streams", 1)):
            cmd.extend(["-map", f"1:a:{i}?"])
        cmd.append(output_path)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            return

        # Fallback: re-encode audio to AAC
        logger.warning("Audio copy failed, re-encoding to AAC")
        cmd = base_cmd + [
            "-i", original_video,
            "-c:v", encoder, *encoder_opts,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0",
        ]
        for i in range(info.get("audio_streams", 1)):
            cmd.extend(["-map", f"1:a:{i}?"])
        cmd.append(output_path)

        subprocess.run(cmd, capture_output=True, check=True)
    else:
        # No audio
        cmd = base_cmd + [
            "-c:v", encoder, *encoder_opts,
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)


def apply_multi_scene_lut(
    video_path: str,
    luts: list[np.ndarray],
    cluster_profiles: list[dict],
    output_path: str,
    quality: int = 18,
    strength: float = 1.0,
    auto_wb: bool = False,
    use_gpu: bool = False,
) -> str:
    """Apply multiple LUTs to a video, selecting per-frame based on scene cluster.

    Args:
        video_path: Path to the raw footage.
        luts: List of 3D LUT arrays, one per cluster.
        cluster_profiles: List of color profiles, one per cluster.
        output_path: Destination path.
        quality: CRF quality value.
        strength: Grade intensity.
        auto_wb: Apply auto white balance before grading.
        use_gpu: Try GPU encoding.

    Returns:
        Output file path.
    """
    from renderiq.analyzer import classify_frame

    info = get_video_info(video_path)
    total_frames = int(info["duration"] * info["fps"])
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    temp_video = output_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        temp_video, fourcc, info["fps"],
        (info["width"], info["height"])
    )

    if not writer.isOpened():
        cap.release()
        raise IOError(f"Cannot create output video: {temp_video}")

    with tqdm(total=total_frames, desc="Multi-scene grading", unit="frame") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if auto_wb:
                rgb = auto_white_balance(rgb)

            # Classify frame to pick the right LUT
            cluster_idx = classify_frame(rgb, cluster_profiles)
            lut = luts[cluster_idx]

            graded = apply_lut_to_frame(rgb, lut, strength=strength)
            bgr = cv2.cvtColor(graded, cv2.COLOR_RGB2BGR)
            writer.write(bgr)
            pbar.update(1)

    cap.release()
    writer.release()

    encoder = "libx264"
    encoder_opts = ["-crf", str(quality)]
    if use_gpu and check_gpu_available():
        encoder = "h264_nvenc"
        encoder_opts = ["-preset", "medium", "-qp", str(quality)]

    _mux_audio(temp_video, video_path, output_path, info, encoder, encoder_opts)

    if os.path.exists(temp_video):
        os.remove(temp_video)

    logger.info("Multi-scene graded video saved to %s", output_path)
    return output_path


def preview_grade(
    video_path: str,
    lut: np.ndarray,
    timestamp: float | None = None,
    strength: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (original_frame, graded_frame) for quick visual comparison.

    Args:
        video_path: Path to the video file.
        lut: 3D LUT array.
        timestamp: Time in seconds to extract frame. If None, uses midpoint.
        strength: Grade intensity 0.0-1.0.

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
    graded = apply_lut_to_frame(original, lut, strength=strength)
    return original, graded
