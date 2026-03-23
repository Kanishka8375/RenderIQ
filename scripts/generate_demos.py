#!/usr/bin/env python3
"""Generate 10 before/after demo comparison images for marketing.

Creates synthetic test footage in 5 different styles, applies the 2 best presets
(cinematic_warm and teal_orange), and generates comparison images.

Usage:
    python scripts/generate_demos.py
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

DEMOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demos")
os.makedirs(DEMOS_DIR, exist_ok=True)

# Presets to showcase
SHOWCASE_PRESETS = ["cinematic_warm", "teal_orange"]

# Synthetic scene generators — each creates a representative 640x360 frame
def _scene_vlog():
    """Person-like warm interior scene."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # Warm background gradient
    for y in range(360):
        for x in range(640):
            t_x = x / 640
            t_y = y / 360
            r = int(180 - 40 * t_y + 20 * t_x)
            g = int(140 - 30 * t_y + 10 * t_x)
            b = int(100 - 20 * t_y)
            frame[y, x] = [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]
    # Add skin-tone circle (face placeholder)
    cv2.circle(frame, (320, 150), 60, (200, 160, 130), -1)
    cv2.circle(frame, (320, 150), 62, (180, 140, 110), 2)
    return frame


def _scene_city_night():
    """City skyline at night with lights."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # Dark blue sky gradient
    for y in range(200):
        t = y / 200
        frame[y, :] = [int(10 + 15 * t), int(15 + 20 * t), int(40 + 30 * t)]
    # Darker ground
    frame[200:, :] = [20, 20, 30]
    # Buildings as rectangles
    np.random.seed(42)
    for _ in range(15):
        x = np.random.randint(0, 600)
        w = np.random.randint(20, 60)
        h = np.random.randint(80, 180)
        y_base = 200
        color = (np.random.randint(30, 60), np.random.randint(30, 60), np.random.randint(40, 80))
        cv2.rectangle(frame, (x, y_base - h), (x + w, y_base), color, -1)
        # Windows (yellow dots)
        for wy in range(y_base - h + 10, y_base - 5, 15):
            for wx in range(x + 5, x + w - 5, 12):
                if np.random.random() > 0.3:
                    cv2.rectangle(frame, (wx, wy), (wx + 4, wy + 6), (200, 180, 80), -1)
    return frame


def _scene_nature():
    """Forest/nature landscape."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # Sky
    for y in range(180):
        t = y / 180
        frame[y, :] = [int(140 + 60 * t), int(180 + 30 * t), int(220 - 20 * t)]
    # Green hills
    for x in range(640):
        hill_h = int(180 + 30 * np.sin(x / 80) + 15 * np.sin(x / 30))
        for y in range(hill_h, 360):
            t = (y - hill_h) / (360 - hill_h + 1)
            g = int(100 - 40 * t + 20 * np.sin(x / 20))
            frame[y, x] = [max(0, min(255, int(40 - 10 * t))), max(0, min(255, g)), max(0, min(255, int(25 - 10 * t)))]
    # Tree silhouettes
    for tx in [100, 250, 400, 520]:
        h = np.random.randint(60, 120)
        cv2.rectangle(frame, (tx, 180 - h), (tx + 8, 180), (30, 50, 25), -1)
        cv2.circle(frame, (tx + 4, 180 - h), 30, (35, 65, 30), -1)
    return frame


def _scene_food():
    """Overhead food/cooking shot."""
    frame = np.full((360, 640, 3), (200, 185, 170), dtype=np.uint8)  # Light wood table
    # Add texture noise
    noise = np.random.randint(-10, 10, frame.shape, dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    # Plate (white circle)
    cv2.circle(frame, (320, 180), 100, (240, 240, 235), -1)
    cv2.circle(frame, (320, 180), 102, (200, 195, 190), 2)
    # Food items
    cv2.circle(frame, (300, 160), 30, (180, 80, 40), -1)  # Brown (meat)
    cv2.circle(frame, (350, 170), 20, (60, 140, 50), -1)  # Green (vegetable)
    cv2.circle(frame, (310, 200), 25, (220, 180, 60), -1)  # Yellow (grain)
    # Small bowl
    cv2.circle(frame, (500, 120), 40, (230, 225, 220), -1)
    cv2.circle(frame, (500, 120), 42, (190, 185, 180), 2)
    return frame


def _scene_interior():
    """Indoor room/workspace."""
    frame = np.full((360, 640, 3), (160, 155, 150), dtype=np.uint8)  # Wall
    # Floor (darker)
    frame[240:, :] = [100, 95, 90]
    # Window (bright rectangle)
    cv2.rectangle(frame, (400, 40), (580, 200), (220, 230, 240), -1)
    cv2.rectangle(frame, (400, 40), (580, 200), (180, 180, 180), 2)
    cv2.line(frame, (490, 40), (490, 200), (180, 180, 180), 2)
    cv2.line(frame, (400, 120), (580, 120), (180, 180, 180), 2)
    # Desk
    cv2.rectangle(frame, (50, 200), (350, 220), (120, 80, 50), -1)
    # Monitor
    cv2.rectangle(frame, (130, 100), (280, 200), (30, 30, 35), -1)
    cv2.rectangle(frame, (135, 105), (275, 195), (80, 100, 120), -1)
    # Lamp glow
    cv2.circle(frame, (500, 160), 60, (200, 195, 180), -1)
    return frame


SCENES = [
    ("vlog", _scene_vlog),
    ("city_night", _scene_city_night),
    ("nature", _scene_nature),
    ("food", _scene_food),
    ("interior", _scene_interior),
]


def main():
    print("Generating demo comparison images...")

    # Ensure presets exist
    if not os.path.isdir(PRESETS_DIR) or len(os.listdir(PRESETS_DIR)) < 10:
        print("Generating presets first...")
        generate_all_presets()

    count = 0
    for scene_name, scene_fn in SCENES:
        frame = scene_fn()
        for preset_name in SHOWCASE_PRESETS:
            lut = load_cube(get_preset_path(preset_name))
            graded = apply_lut_to_frame(frame, lut, strength=0.85)
            comp = create_comparison(frame, graded, mode="side_by_side")

            # Save comparison
            out_path = os.path.join(DEMOS_DIR, f"{scene_name}_{preset_name}.png")
            bgr = cv2.cvtColor(comp, cv2.COLOR_RGB2BGR)
            cv2.imwrite(out_path, bgr)
            count += 1
            print(f"  [{count}/10] {scene_name} + {preset_name}")

    print(f"\nDone! {count} demo images saved to {DEMOS_DIR}/")


if __name__ == "__main__":
    main()
