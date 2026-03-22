"""End-to-end orchestration for the RenderIQ color grade transfer pipeline.

Ties together sampling, analysis, LUT generation, and video grading
into a single pipeline with timing and logging.
"""

import logging
import os
import time

from renderiq.sampler import extract_keyframes
from renderiq.analyzer import analyze_color_profile, cluster_keyframes
from renderiq.lut_generator import generate_lut, export_cube
from renderiq.grader import apply_lut_to_video, apply_multi_scene_lut
from renderiq.utils import validate_video

logger = logging.getLogger(__name__)


def process(
    reference_path: str,
    raw_footage_path: str | None = None,
    output_dir: str = "output/",
    lut_only: bool = False,
    preset_name: str | None = None,
    multi_scene: bool = False,
    strength: float = 1.0,
    auto_wb: bool = False,
    workers: int | None = None,
    use_gpu: bool = False,
) -> dict:
    """Run the full RenderIQ pipeline.

    Args:
        reference_path: Path to the reference video (style source).
        raw_footage_path: Path to raw footage to grade. Required unless lut_only.
        output_dir: Directory for output files.
        lut_only: If True, only generate the .cube LUT file.
        preset_name: If provided, save .cube to presets/ with this name.
        multi_scene: If True, cluster reference into scenes and generate per-scene LUTs.
        strength: Grade intensity 0.0-1.0 (default 1.0).
        auto_wb: Apply auto white balance before grading.
        workers: Number of parallel workers for grading.
        use_gpu: Try to use GPU encoding.

    Returns:
        Dict with lut_path, graded_video_path, color_profile,
        processing_time, and per-step timing info.
    """
    start_time = time.time()
    steps = []

    # Validate inputs
    validation = validate_video(reference_path)
    if validation is not True:
        error = validation.get("error", "Unknown error") if isinstance(validation, dict) else "Invalid video"
        raise ValueError(f"Invalid reference video: {error}")
    if raw_footage_path and not lut_only:
        validation = validate_video(raw_footage_path)
        if validation is not True:
            error = validation.get("error", "Unknown error") if isinstance(validation, dict) else "Invalid video"
            raise ValueError(f"Invalid raw footage video: {error}")

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Sample keyframes from reference
    step_start = time.time()
    logger.info("Step 1: Extracting keyframes from reference...")
    ref_keyframes = extract_keyframes(reference_path)
    steps.append({"step": "sample_reference", "time": time.time() - step_start})

    # Step 2: Analyze reference color profile
    step_start = time.time()
    logger.info("Step 2: Analyzing reference color profile...")

    if multi_scene:
        # Multi-scene: cluster keyframes and generate per-cluster profiles + LUTs
        clusters = cluster_keyframes(ref_keyframes, n_clusters=3)
        logger.info("Found %d scene clusters", len(clusters))
        cluster_profiles = [analyze_color_profile(c) for c in clusters]
        ref_profile = cluster_profiles[0]  # Use first cluster as primary for metadata
    else:
        ref_profile = analyze_color_profile(ref_keyframes)
        clusters = None
        cluster_profiles = None

    steps.append({"step": "analyze_reference", "time": time.time() - step_start})

    # Step 3: Build source profile
    src_profile = None
    if raw_footage_path and not lut_only:
        step_start = time.time()
        logger.info("Step 3: Extracting keyframes from raw footage...")
        src_keyframes = extract_keyframes(raw_footage_path)
        src_profile = analyze_color_profile(src_keyframes)
        steps.append({"step": "analyze_source", "time": time.time() - step_start})
    else:
        step_start = time.time()
        logger.info("Step 3: Building neutral source profile...")
        src_profile = _build_neutral_profile()
        steps.append({"step": "build_neutral_profile", "time": time.time() - step_start})

    # Step 4: Generate LUT(s)
    step_start = time.time()
    logger.info("Step 4: Generating 3D LUT...")

    if multi_scene and cluster_profiles:
        luts = [generate_lut(src_profile, cp) for cp in cluster_profiles]
        lut = luts[0]
    else:
        lut = generate_lut(src_profile, ref_profile)
        luts = None

    steps.append({"step": "generate_lut", "time": time.time() - step_start})

    # Step 5: Export .cube file(s)
    step_start = time.time()
    if preset_name:
        lut_path = os.path.join("presets", f"{preset_name}.cube")
    else:
        base = os.path.splitext(os.path.basename(reference_path))[0]
        lut_path = os.path.join(output_dir, f"{base}_lut.cube")

    export_cube(lut, lut_path)

    # Export multi-scene LUTs
    multi_scene_paths = []
    if multi_scene and luts:
        base_name = preset_name or os.path.splitext(os.path.basename(reference_path))[0]
        target_dir = "presets" if preset_name else output_dir
        for i, scene_lut in enumerate(luts):
            scene_path = os.path.join(target_dir, f"{base_name}_scene{i + 1}.cube")
            export_cube(scene_lut, scene_path, title=f"RenderIQ Scene {i + 1}")
            multi_scene_paths.append(scene_path)

    steps.append({"step": "export_cube", "time": time.time() - step_start})

    # Step 6: Apply LUT to raw footage
    graded_path = None
    if raw_footage_path and not lut_only:
        step_start = time.time()
        logger.info("Step 5: Applying LUT to raw footage...")
        base = os.path.splitext(os.path.basename(raw_footage_path))[0]
        graded_path = os.path.join(output_dir, f"{base}_graded.mp4")

        if multi_scene and luts and cluster_profiles:
            apply_multi_scene_lut(
                raw_footage_path, luts, cluster_profiles, graded_path,
                strength=strength, auto_wb=auto_wb, use_gpu=use_gpu,
            )
        else:
            apply_lut_to_video(
                raw_footage_path, lut, graded_path,
                strength=strength, auto_wb=auto_wb,
                workers=workers, use_gpu=use_gpu,
            )
        steps.append({"step": "apply_lut", "time": time.time() - step_start})

    total_time = time.time() - start_time
    logger.info("Pipeline complete in %.1f seconds", total_time)

    return {
        "lut_path": lut_path,
        "multi_scene_paths": multi_scene_paths,
        "graded_video_path": graded_path,
        "color_profile": ref_profile,
        "processing_time": total_time,
        "steps": steps,
    }


def _build_neutral_profile() -> dict:
    """Build a neutral/flat color profile representing ungraded footage.

    This creates a uniform histogram distribution, so the LUT will
    map neutral colors to the reference style.
    """
    uniform_hist = [1.0 / 256] * 256

    neutral_stats = {}
    for name in ["R", "G", "B"]:
        neutral_stats[name] = {
            "mean": 127.5,
            "median": 127.5,
            "std": 73.9,
            "percentiles": {
                "p1": 2.55, "p5": 12.75, "p25": 63.75,
                "p50": 127.5, "p75": 191.25, "p95": 242.25, "p99": 252.45,
            },
        }

    neutral_hsv_stats = {}
    for name in ["H", "S", "V"]:
        neutral_hsv_stats[name] = {
            "mean": 127.5,
            "median": 127.5,
            "std": 73.9,
            "percentiles": {
                "p1": 2.55, "p5": 12.75, "p25": 63.75,
                "p50": 127.5, "p75": 191.25, "p95": 242.25, "p99": 252.45,
            },
        }

    neutral_lab_stats = {}
    for name in ["L", "A", "B"]:
        neutral_lab_stats[name] = {
            "mean": 127.5,
            "median": 127.5,
            "std": 73.9,
            "percentiles": {
                "p1": 2.55, "p5": 12.75, "p25": 63.75,
                "p50": 127.5, "p75": 191.25, "p95": 242.25, "p99": 252.45,
            },
        }

    return {
        "rgb": {
            "histograms": {n: uniform_hist for n in ["R", "G", "B"]},
            "stats": neutral_stats,
        },
        "hsv": {
            "histograms": {n: uniform_hist for n in ["H", "S", "V"]},
            "stats": neutral_hsv_stats,
        },
        "lab": {
            "histograms": {n: uniform_hist for n in ["L", "A", "B"]},
            "stats": neutral_lab_stats,
        },
        "dominant_colors": [[127, 128, 128]] * 8,
        "frame_count": 0,
        "metadata": {"avg_brightness": 127.5, "avg_saturation": 127.5},
        "warnings": {
            "overexposed_frames": 0,
            "underexposed_frames": 0,
            "total_frames": 0,
        },
    }
