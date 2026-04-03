"""
Text & Titles Module (Module 13)
Auto-generate intro titles, lower thirds, and end cards.
Uses FFmpeg drawtext filter.
"""
import subprocess
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def add_text_overlays(
    video_path: str,
    output_path: str,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    end_text: Optional[str] = None,
    style: str = "cinematic",
    progress_callback=None,
) -> str:
    """
    Add text overlays to video.

    - title: shown at start (first 3s, centered, large)
    - subtitle: shown below title (first 3s, smaller)
    - end_text: shown at end (last 4s, centered)
    """
    if progress_callback:
        progress_callback("Adding text overlays...", 78)

    if not title and not end_text:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    duration = _get_duration(video_path)

    styles = {
        "cinematic": {"title_size": 64, "sub_size": 32, "color": "white", "shadow": 2},
        "bold": {"title_size": 72, "sub_size": 36, "color": "white", "shadow": 3},
        "minimal": {"title_size": 48, "sub_size": 24, "color": "white@0.8", "shadow": 1},
    }

    s = styles.get(style, styles["cinematic"])
    filters = []

    # Find a usable font path
    font_bold = _find_font("bold")
    font_regular = _find_font("regular")

    alpha_expr = (
        "if(lt(t,0.5),t/0.5,"
        "if(lt(t,2.5),1,"
        "if(lt(t,3.0),(3.0-t)/0.5,0)))"
    )

    if title:
        title_escaped = _escape_drawtext(title)
        filters.append(
            f"drawtext=text='{title_escaped}'"
            f":fontfile={font_bold}"
            f":fontsize={s['title_size']}"
            f":fontcolor={s['color']}"
            f":shadowcolor=black:shadowx={s['shadow']}:shadowy={s['shadow']}"
            f":x=(w-text_w)/2:y=(h-text_h)/2-30"
            f":alpha='{alpha_expr}'"
            f":enable='between(t,0,3)'"
        )

        if subtitle:
            sub_escaped = _escape_drawtext(subtitle)
            filters.append(
                f"drawtext=text='{sub_escaped}'"
                f":fontfile={font_regular}"
                f":fontsize={s['sub_size']}"
                f":fontcolor={s['color']}"
                f":shadowcolor=black:shadowx=1:shadowy=1"
                f":x=(w-text_w)/2:y=(h/2)+30"
                f":alpha='{alpha_expr}'"
                f":enable='between(t,0,3)'"
            )

    if end_text and duration > 5:
        end_escaped = _escape_drawtext(end_text)
        end_start = duration - 4.0
        end_alpha = (
            f"if(lt(t-{end_start},0.5),(t-{end_start})/0.5,"
            f"if(lt(t-{end_start},3.5),1,"
            f"if(lt(t-{end_start},4.0),(4.0-(t-{end_start}))/0.5,0)))"
        )
        filters.append(
            f"drawtext=text='{end_escaped}'"
            f":fontfile={font_bold}"
            f":fontsize={s['title_size']}"
            f":fontcolor={s['color']}"
            f":shadowcolor=black:shadowx={s['shadow']}:shadowy={s['shadow']}"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
            f":alpha='{end_alpha}'"
            f":enable='gte(t,{end_start})'"
        )

    if not filters:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning("Text overlay failed: %s", result.stderr[-200:])
        import shutil
        shutil.copy2(video_path, output_path)

    if progress_callback:
        progress_callback("Text overlays added", 82)

    return output_path


def _escape_drawtext(text: str) -> str:
    """Escape text for FFmpeg drawtext filter."""
    # Backslashes must be escaped first to avoid double-escaping
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    text = text.replace("%", "%%")
    text = text.replace("\n", " ")
    return text


def _find_font(style: str = "bold") -> str:
    """Find a usable font file on the system."""
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    paths = bold_paths if style == "bold" else regular_paths
    for p in paths:
        if os.path.exists(p):
            return p

    # Fallback
    return paths[0]


def _get_duration(path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 60.0
