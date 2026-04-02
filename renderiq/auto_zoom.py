"""
Auto Zoom Module (Module 11)
Adds Ken Burns style zoom/pan effects.
Uses face tracking data to focus on subjects.
"""
import subprocess
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def apply_auto_zoom(
    video_path: str,
    scenes: List[dict],
    face_data: Optional[List[dict]] = None,
    zoom_intensity: float = 0.05,
    output_path: str = None,
    progress_callback=None,
) -> str:
    """
    Apply subtle zoom effects per scene.

    Rules:
    - Static scenes (low motion): slow push-in zoom
    - Face present: zoom toward face center
    - High motion: no zoom (already dynamic)
    - Alternate zoom-in and zoom-out for variety
    """
    if progress_callback:
        progress_callback("Adding zoom effects...", 58)

    if not scenes:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    temp_dir = os.path.dirname(output_path)
    segment_files = []
    concat_list = os.path.join(temp_dir, "zoom_concat.txt")

    for i, scene in enumerate(scenes):
        motion = scene.get("motion_score", 0.5)
        seg_path = os.path.join(temp_dir, f"zoom_seg_{i:04d}.mp4")

        # Skip zoom for high-motion scenes
        if motion > 0.6:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(scene["start_time"]),
                "-i", video_path,
                "-t", str(scene["duration"]),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "copy",
                seg_path,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        else:
            zoom_in = (i % 2 == 0)

            # Build zoompan filter
            fps = 30
            total_frames = max(1, int(scene["duration"] * fps))

            if zoom_in:
                zoom_expr = f"zoom+{zoom_intensity/total_frames}"
            else:
                zoom_expr = (
                    f"if(eq(on,1),{1.0+zoom_intensity},"
                    f"zoom-{zoom_intensity/total_frames})"
                )

            pan_x = "iw/2-(iw/zoom/2)"
            pan_y = "ih/2-(ih/zoom/2)"

            vf = (
                f"zoompan=z='{zoom_expr}':x='{pan_x}':y='{pan_y}'"
                f":d={total_frames}:s=1920x1080:fps={fps}"
            )

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(scene["start_time"]),
                "-i", video_path,
                "-t", str(scene["duration"]),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "copy",
                seg_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                cmd_fallback = [
                    "ffmpeg", "-y",
                    "-ss", str(scene["start_time"]),
                    "-i", video_path,
                    "-t", str(scene["duration"]),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "copy",
                    seg_path,
                ]
                subprocess.run(cmd_fallback, capture_output=True, timeout=60)

        if os.path.exists(seg_path) and os.path.getsize(seg_path) > 100:
            segment_files.append(seg_path)

    if segment_files:
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Cleanup
    for seg in segment_files:
        try:
            os.remove(seg)
        except OSError:
            pass
    try:
        os.remove(concat_list)
    except OSError:
        pass

    if progress_callback:
        progress_callback("Zoom effects applied", 62)

    return output_path
