"""
Smart Cuts Module (Module 4)
Remove boring scenes, keep highlights.
Uses scene interest scores to decide what to keep.
"""
import subprocess
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

# Pacing configs: what % of scenes to keep
PACING_CONFIG = {
    "slow": {"keep_ratio": 0.9, "min_interest": 0.15},
    "medium": {"keep_ratio": 0.7, "min_interest": 0.3},
    "fast": {"keep_ratio": 0.5, "min_interest": 0.4},
}


def smart_cut(
    video_path: str,
    scenes: List[dict],
    pacing: str = "medium",
    output_path: str = None,
    progress_callback=None,
) -> dict:
    """
    Remove low-interest scenes to create a tighter edit.

    Returns dict with output_path and kept_scenes list.
    """
    if progress_callback:
        progress_callback("Making smart cuts...", 30)

    config = PACING_CONFIG.get(pacing, PACING_CONFIG["medium"])

    if not scenes:
        import shutil
        shutil.copy2(video_path, output_path)
        return {"output_path": output_path, "kept_scenes": []}

    # Sort by interest and keep top N%
    sorted_scenes = sorted(scenes, key=lambda s: s.get("interest_score", 0), reverse=True)
    keep_count = max(1, int(len(sorted_scenes) * config["keep_ratio"]))
    kept = sorted_scenes[:keep_count]

    # Also filter by minimum interest threshold
    kept = [s for s in kept if s.get("interest_score", 0) >= config["min_interest"]]
    if not kept:
        kept = sorted_scenes[:1]  # Keep at least one scene

    # Re-sort by time order
    kept.sort(key=lambda s: s["start_time"])

    # Assemble the kept scenes
    _assemble_cuts(video_path, kept, output_path)

    removed = len(scenes) - len(kept)
    logger.info("Smart cuts: kept %d/%d scenes (removed %d)", len(kept), len(scenes), removed)

    if progress_callback:
        progress_callback(f"Kept {len(kept)}/{len(scenes)} scenes", 38)

    return {"output_path": output_path, "kept_scenes": kept}


def _assemble_cuts(video_path: str, scenes: List[dict], output_path: str):
    """Extract and concatenate selected scenes using FFmpeg."""
    temp_dir = os.path.dirname(output_path)
    segment_files = []
    concat_list = os.path.join(temp_dir, "cut_concat.txt")

    for i, scene in enumerate(scenes):
        seg_path = os.path.join(temp_dir, f"cut_seg_{i:04d}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(scene["start_time"]),
            "-i", video_path,
            "-t", str(scene["duration"]),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            seg_path,
        ]

        subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if os.path.exists(seg_path) and os.path.getsize(seg_path) > 100:
            segment_files.append(seg_path)

    if not segment_files:
        import shutil
        shutil.copy2(video_path, output_path)
        return

    # Concatenate
    with open(concat_list, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Cleanup temp segments
    for seg in segment_files:
        try:
            os.remove(seg)
        except OSError:
            pass
    try:
        os.remove(concat_list)
    except OSError:
        pass

    if result.returncode != 0:
        logger.warning("Concat failed: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)
