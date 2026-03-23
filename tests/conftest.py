"""Shared test fixtures for RenderIQ tests."""

import os
import subprocess
import tempfile

import cv2
import numpy as np
import pytest


@pytest.fixture(autouse=True)
def disable_rate_limit(monkeypatch):
    """Disable rate limiting for all tests."""
    monkeypatch.setenv("TESTING", "1")


@pytest.fixture
def sample_video(tmp_path):
    """Create a short synthetic test video (3 seconds, 30fps, 320x240)."""
    path = str(tmp_path / "test_video.mp4")
    fps = 30
    duration = 3
    width, height = 320, 240

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(42)
    for i in range(fps * duration):
        # Transition from warm to cool tones over the video
        t = i / (fps * duration)
        r = int(200 * (1 - t) + 50 * t)
        g = int(100 + 50 * t)
        b = int(50 * (1 - t) + 200 * t)
        frame = np.full((height, width, 3), [b, g, r], dtype=np.uint8)
        # Add some noise for realism
        noise = rng.integers(-20, 20, (height, width, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        writer.write(frame)

    writer.release()
    return path


@pytest.fixture
def warm_video(tmp_path):
    """Create a warm-toned test video (orange/amber tones)."""
    path = str(tmp_path / "warm_video.mp4")
    fps = 30
    duration = 2
    width, height = 320, 240

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(100)
    for i in range(fps * duration):
        frame = np.full((height, width, 3), [30, 100, 210], dtype=np.uint8)
        noise = rng.integers(-15, 15, (height, width, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        writer.write(frame)

    writer.release()
    return path


@pytest.fixture
def cool_video(tmp_path):
    """Create a cool-toned test video (blue/teal tones)."""
    path = str(tmp_path / "cool_video.mp4")
    fps = 30
    duration = 2
    width, height = 320, 240

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(200)
    for i in range(fps * duration):
        frame = np.full((height, width, 3), [200, 140, 60], dtype=np.uint8)
        noise = rng.integers(-15, 15, (height, width, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        writer.write(frame)

    writer.release()
    return path


@pytest.fixture
def high_contrast_video(tmp_path):
    """Create a high-contrast test video."""
    path = str(tmp_path / "contrast_video.mp4")
    fps = 30
    duration = 2
    width, height = 320, 240

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(300)
    for i in range(fps * duration):
        # Checkerboard of bright and dark
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:height // 2, :width // 2] = [240, 240, 240]
        frame[height // 2:, width // 2:] = [240, 240, 240]
        frame[:height // 2, width // 2:] = [15, 15, 15]
        frame[height // 2:, :width // 2] = [15, 15, 15]
        noise = rng.integers(-5, 5, (height, width, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        writer.write(frame)

    writer.release()
    return path


@pytest.fixture
def scene_change_video(tmp_path):
    """Create a video with distinct scene changes."""
    path = str(tmp_path / "scene_change_video.mp4")
    fps = 30
    width, height = 320, 240

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    rng = np.random.default_rng(400)
    scenes = [
        ([30, 50, 180], 30),   # 1s warm
        ([200, 150, 50], 30),  # 1s cool
        ([50, 180, 50], 30),   # 1s green
        ([150, 50, 200], 30),  # 1s purple
    ]

    for color, num_frames in scenes:
        for _ in range(num_frames):
            frame = np.full((height, width, 3), color, dtype=np.uint8)
            noise = rng.integers(-10, 10, (height, width, 3), dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            writer.write(frame)

    writer.release()
    return path


@pytest.fixture
def sample_keyframes():
    """Create sample keyframes (RGB numpy arrays) for testing."""
    rng = np.random.default_rng(42)
    frames = []
    for i in range(10):
        # Create frames with varying warm tones
        frame = np.full((240, 320, 3), [200, 100, 50], dtype=np.uint8)
        noise = rng.integers(-30, 30, (240, 320, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frames.append({
            "frame": frame,
            "timestamp": float(i * 2),
            "source": "uniform",
        })
    return frames


@pytest.fixture
def identity_lut():
    """Create an identity LUT (no color change)."""
    size = 17  # Smaller for faster tests
    lut = np.zeros((size, size, size, 3), dtype=np.float32)
    grid = np.linspace(0, 1, size, dtype=np.float32)
    for ri, r in enumerate(grid):
        for gi, g in enumerate(grid):
            for bi, b in enumerate(grid):
                lut[ri, gi, bi] = [r, g, b]
    return lut


def make_video_ffmpeg(path, width=320, height=240, fps=30, duration=3,
                      color="808080", has_audio=True, codec="libx264"):
    """Create a test video using FFmpeg with precise control."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=#{color}:s={width}x{height}:d={duration}:r={fps}",
    ]
    if has_audio:
        cmd += [
            "-f", "lavfi", "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:a", "aac", "-b:a", "128k",
        ]
    cmd += [
        "-c:v", codec, "-pix_fmt", "yuv420p",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return str(path)
