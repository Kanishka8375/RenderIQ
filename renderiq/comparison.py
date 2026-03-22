"""Before/after comparison image generation.

Creates professional-looking side-by-side and slider comparison images
for marketing and preview purposes.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


TARGET_HEIGHT = 1080


def create_comparison(
    original: np.ndarray,
    graded: np.ndarray,
    mode: str = "side_by_side",
) -> np.ndarray:
    """Generate a professional before/after comparison image.

    Args:
        original: RGB numpy array of the original frame.
        graded: RGB numpy array of the graded frame.
        mode: "side_by_side" or "slider".

    Returns:
        RGB numpy array of the comparison image at 1080p height.
    """
    # Resize both to target height while preserving aspect ratio
    orig_resized = _resize_to_height(original, TARGET_HEIGHT)
    grad_resized = _resize_to_height(graded, TARGET_HEIGHT)

    # Ensure both have same dimensions
    min_w = min(orig_resized.shape[1], grad_resized.shape[1])
    orig_resized = orig_resized[:, :min_w]
    grad_resized = grad_resized[:, :min_w]

    if mode == "slider":
        return _slider_view(orig_resized, grad_resized)
    else:
        return _side_by_side(orig_resized, grad_resized)


def _resize_to_height(frame: np.ndarray, target_h: int) -> np.ndarray:
    """Resize frame to target height, preserving aspect ratio."""
    h, w = frame.shape[:2]
    if h == target_h:
        return frame
    scale = target_h / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)


def _side_by_side(original: np.ndarray, graded: np.ndarray) -> np.ndarray:
    """Create side-by-side comparison with divider and labels."""
    h, w, _ = original.shape

    # Create divider (thin white line)
    divider_width = 4
    divider = np.full((h, divider_width, 3), 255, dtype=np.uint8)

    # Combine
    result = np.hstack([original, divider, graded])

    # Add labels using PIL for text rendering
    result = _add_labels(result, w, divider_width)

    return result


def _slider_view(original: np.ndarray, graded: np.ndarray) -> np.ndarray:
    """Create slider view with left half original, right half graded."""
    h, w, _ = original.shape
    mid = w // 2

    result = np.copy(graded)
    result[:, :mid] = original[:, :mid]

    # Draw white vertical line at midpoint
    line_width = 3
    half = line_width // 2
    result[:, max(0, mid - half):mid + half + 1] = 255

    # Add labels
    result = _add_labels_single(result, mid)

    return result


def _add_labels(image: np.ndarray, panel_width: int, divider_width: int) -> np.ndarray:
    """Add ORIGINAL and RenderIQ labels to a side-by-side image."""
    pil_img = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_img)

    font_size = 36
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Background rectangles for readability
    margin = 20
    padding = 10

    # "ORIGINAL" label on left panel
    text_l = "ORIGINAL"
    bbox_l = draw.textbbox((0, 0), text_l, font=font)
    tw_l = bbox_l[2] - bbox_l[0]
    th_l = bbox_l[3] - bbox_l[1]
    x_l = margin
    y_l = image.shape[0] - th_l - margin - padding * 2

    draw.rectangle(
        [x_l, y_l, x_l + tw_l + padding * 2, y_l + th_l + padding * 2],
        fill=(0, 0, 0, 180),
    )
    draw.text((x_l + padding, y_l + padding), text_l, fill=(255, 255, 255), font=font)

    # "RenderIQ" label on right panel
    text_r = "RenderIQ"
    bbox_r = draw.textbbox((0, 0), text_r, font=font)
    tw_r = bbox_r[2] - bbox_r[0]
    th_r = bbox_r[3] - bbox_r[1]
    x_r = panel_width + divider_width + margin
    y_r = image.shape[0] - th_r - margin - padding * 2

    draw.rectangle(
        [x_r, y_r, x_r + tw_r + padding * 2, y_r + th_r + padding * 2],
        fill=(0, 0, 0, 180),
    )
    draw.text((x_r + padding, y_r + padding), text_r, fill=(255, 255, 255), font=font)

    return np.array(pil_img)


def _add_labels_single(image: np.ndarray, midpoint: int) -> np.ndarray:
    """Add labels to a single slider image."""
    pil_img = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_img)

    font_size = 36
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    margin = 20
    padding = 10
    h = image.shape[0]

    # "ORIGINAL" on left
    text_l = "ORIGINAL"
    bbox_l = draw.textbbox((0, 0), text_l, font=font)
    tw_l = bbox_l[2] - bbox_l[0]
    th_l = bbox_l[3] - bbox_l[1]
    y = h - th_l - margin - padding * 2

    draw.rectangle(
        [margin, y, margin + tw_l + padding * 2, y + th_l + padding * 2],
        fill=(0, 0, 0, 180),
    )
    draw.text((margin + padding, y + padding), text_l, fill=(255, 255, 255), font=font)

    # "RenderIQ" on right
    text_r = "RenderIQ"
    bbox_r = draw.textbbox((0, 0), text_r, font=font)
    tw_r = bbox_r[2] - bbox_r[0]
    x_r = midpoint + margin

    draw.rectangle(
        [x_r, y, x_r + tw_r + padding * 2, y + th_l + padding * 2],
        fill=(0, 0, 0, 180),
    )
    draw.text((x_r + padding, y + padding), text_r, fill=(255, 255, 255), font=font)

    return np.array(pil_img)
