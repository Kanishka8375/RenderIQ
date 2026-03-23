#!/usr/bin/env python3
"""Create a 60-second demo video showcasing RenderIQ.

Generates a screen-recording-style video with text overlays showing:
- Logo + tagline
- Upload step
- Preset selection
- Processing
- Before/after reveal
- CTA

Usage:
    python scripts/create_demo_video.py
"""

import os
import sys
import subprocess
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from renderiq.presets_builder import get_preset_path, generate_all_presets, PRESETS_DIR
from renderiq.lut_generator import load_cube
from renderiq.grader import apply_lut_to_frame
from renderiq.comparison import create_comparison

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 1080, 1920  # Vertical (Shorts/Reels format)
FPS = 30
BG_COLOR = (15, 15, 26)       # --color-bg
PRIMARY = (108, 92, 231)      # --color-primary
SECONDARY = (0, 210, 211)     # --color-secondary
TEXT_COLOR = (255, 255, 255)
MUTED = (160, 160, 184)


def _make_frame(bg=None):
    if bg is None:
        return np.full((H, W, 3), BG_COLOR, dtype=np.uint8)
    return bg.copy()


def _put_text(frame, text, pos, scale=1.0, color=TEXT_COLOR, thickness=2):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, pos, font, scale, color, thickness, cv2.LINE_AA)


def _centered_text(frame, text, y, scale=1.0, color=TEXT_COLOR, thickness=2):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x = (W - tw) // 2
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def generate_intro_frames(n_frames):
    """0-5s: Logo + tagline."""
    frames = []
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames  # fade in

        alpha = min(1.0, t * 3)
        color = tuple(int(c * alpha) for c in TEXT_COLOR)
        primary_c = tuple(int(c * alpha) for c in PRIMARY)

        _centered_text(f, "RenderIQ", H // 2 - 60, 2.5, color, 4)
        _centered_text(f, "AI Color Grade Transfer", H // 2 + 20, 1.0, primary_c, 2)
        _centered_text(f, "Make any video cinematic", H // 2 + 80, 0.7, tuple(int(c * alpha) for c in MUTED), 1)
        frames.append(f)
    return frames


def generate_upload_frames(n_frames):
    """5-15s: Upload step mockup."""
    frames = []
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames

        _centered_text(f, "STEP 1", H // 4, 0.8, PRIMARY, 2)
        _centered_text(f, "Upload Your Video", H // 4 + 60, 1.5, TEXT_COLOR, 3)

        # Draw upload box
        bx, by, bw, bh = 140, H // 2 - 150, W - 280, 300
        cv2.rectangle(f, (bx, by), (bx + bw, by + bh), (60, 60, 80), 2)
        _centered_text(f, "Drop video here", by + bh // 2, 0.8, MUTED, 2)

        # Animate progress bar
        if t > 0.3:
            prog = min(1.0, (t - 0.3) / 0.5)
            bar_y = by + bh + 40
            cv2.rectangle(f, (bx, bar_y), (bx + bw, bar_y + 10), (40, 40, 60), -1)
            cv2.rectangle(f, (bx, bar_y), (bx + int(bw * prog), bar_y + 10), PRIMARY, -1)
            _centered_text(f, f"{int(prog * 100)}%", bar_y + 50, 0.7, PRIMARY, 2)

        frames.append(f)
    return frames


def generate_style_frames(n_frames):
    """15-25s: Style selection."""
    frames = []
    preset_names = ["Cinematic Warm", "Teal & Orange", "Vintage Film", "Moody Dark", "Golden Hour"]
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames

        _centered_text(f, "STEP 2", H // 4, 0.8, PRIMARY, 2)
        _centered_text(f, "Pick a Style", H // 4 + 60, 1.5, TEXT_COLOR, 3)

        # Draw preset cards
        selected = min(int(t * 6), 4)
        for j, name in enumerate(preset_names):
            cy = H // 2 - 100 + j * 80
            cx = 160
            cw = W - 320
            border_color = PRIMARY if j == selected else (60, 60, 80)
            thickness = 3 if j == selected else 1
            cv2.rectangle(f, (cx, cy), (cx + cw, cy + 60), border_color, thickness)
            _put_text(f, name, (cx + 20, cy + 40), 0.7, TEXT_COLOR if j == selected else MUTED, 2)

        frames.append(f)
    return frames


def generate_processing_frames(n_frames):
    """25-35s: Processing progress."""
    frames = []
    steps = ["Extracting keyframes...", "Analyzing colors...", "Generating LUT...", "Applying grade...", "Encoding output..."]
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames
        progress = int(t * 100)
        step_idx = min(int(t * len(steps)), len(steps) - 1)

        _centered_text(f, "Processing", H // 3, 1.2, TEXT_COLOR, 3)

        # Progress ring (simplified as arc)
        center = (W // 2, H // 2)
        cv2.ellipse(f, center, (80, 80), -90, 0, 360, (40, 40, 60), 6)
        cv2.ellipse(f, center, (80, 80), -90, 0, int(360 * t), PRIMARY, 6)
        _centered_text(f, f"{progress}%", H // 2 + 15, 1.5, TEXT_COLOR, 3)

        _centered_text(f, steps[step_idx], H // 2 + 130, 0.7, MUTED, 1)
        frames.append(f)
    return frames


def generate_reveal_frames(n_frames):
    """35-50s: Before/after reveal."""
    # Create actual before/after frames
    if not os.path.isdir(PRESETS_DIR) or len(os.listdir(PRESETS_DIR)) < 10:
        generate_all_presets()

    # Nature scene
    scene = np.zeros((360, 640, 3), dtype=np.uint8)
    for y in range(180):
        t = y / 180
        scene[y, :] = [int(140 + 60 * t), int(180 + 30 * t), int(220 - 20 * t)]
    for x in range(640):
        h_val = int(180 + 30 * np.sin(x / 80))
        for y in range(h_val, 360):
            scene[y, x] = [40, max(0, int(100 - 40 * ((y - h_val) / 180))), 25]

    lut = load_cube(get_preset_path("cinematic_warm"))
    graded = apply_lut_to_frame(scene, lut, strength=0.85)

    before_big = cv2.resize(scene, (W - 200, (W - 200) * 360 // 640))
    after_big = cv2.resize(graded, (W - 200, (W - 200) * 360 // 640))

    frames = []
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames

        _centered_text(f, "The Result", H // 6, 1.2, TEXT_COLOR, 3)

        img_y = H // 3
        img_x = 100
        ih = before_big.shape[0]

        # Slider reveal animation
        split = int((W - 200) * min(1.0, t * 1.5))

        # Place before image
        roi = f[img_y:img_y + ih, img_x:img_x + before_big.shape[1]]
        before_bgr = cv2.cvtColor(before_big, cv2.COLOR_RGB2BGR)
        after_bgr = cv2.cvtColor(after_big, cv2.COLOR_RGB2BGR)

        combined = before_bgr.copy()
        if split > 0:
            combined[:, :split] = after_bgr[:, :split]
        roi[:] = combined

        # Slider line
        cv2.line(f, (img_x + split, img_y), (img_x + split, img_y + ih), TEXT_COLOR, 2)

        _put_text(f, "BEFORE", (img_x + 10, img_y + ih + 30), 0.5, MUTED, 1)
        _put_text(f, "AFTER", (img_x + split + 10, img_y + ih + 30), 0.5, PRIMARY, 1)

        frames.append(f)
    return frames


def generate_cta_frames(n_frames):
    """50-60s: CTA."""
    frames = []
    for i in range(n_frames):
        f = _make_frame()
        t = i / n_frames

        _centered_text(f, "Try it free", H // 2 - 80, 2.0, TEXT_COLOR, 4)
        _centered_text(f, "renderiq.in", H // 2 + 20, 1.5, PRIMARY, 3)
        _centered_text(f, "No signup. No credit card.", H // 2 + 100, 0.7, MUTED, 1)
        _centered_text(f, "Just results.", H // 2 + 140, 0.7, MUTED, 1)

        frames.append(f)
    return frames


def main():
    print("Creating demo video...")

    all_frames = []
    sections = [
        ("Intro", generate_intro_frames, 5),
        ("Upload", generate_upload_frames, 10),
        ("Style", generate_style_frames, 10),
        ("Processing", generate_processing_frames, 10),
        ("Reveal", generate_reveal_frames, 15),
        ("CTA", generate_cta_frames, 10),
    ]

    for name, fn, seconds in sections:
        print(f"  Generating {name} ({seconds}s)...")
        all_frames.extend(fn(seconds * FPS))

    # Write to temp file as raw frames, then encode with ffmpeg
    temp_path = os.path.join(OUTPUT_DIR, "demo_raw.mp4")
    out_path = os.path.join(OUTPUT_DIR, "renderiq_demo.mp4")

    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    writer = cv2.VideoWriter(temp_path, fourcc, FPS, (W, H))

    for frame in all_frames:
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        writer.write(bgr)
    writer.release()

    # Re-encode with ffmpeg for better compatibility
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "23",
        out_path,
    ], capture_output=True)

    os.remove(temp_path)
    print(f"\nDone! Demo video saved to {out_path}")
    print(f"Duration: {len(all_frames) / FPS:.0f}s, Resolution: {W}x{H}")


if __name__ == "__main__":
    main()
