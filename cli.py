"""Command-line interface for RenderIQ."""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import webbrowser

import cv2
import numpy as np

from renderiq.pipeline import process
from renderiq.lut_generator import load_cube
from renderiq.grader import apply_lut_to_video, preview_grade
from renderiq.comparison import create_comparison
from renderiq.presets_builder import list_presets, get_preset_path, generate_all_presets
from renderiq.utils import validate_video


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="renderiq",
        description="RenderIQ — AI Color Grade Transfer Tool",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- lut command ---
    lut_parser = subparsers.add_parser(
        "lut", help="Generate a .cube LUT from a reference video"
    )
    lut_parser.add_argument(
        "--reference", required=True, help="Reference video path"
    )
    lut_parser.add_argument(
        "--output", default=None, help="Output .cube file path"
    )
    lut_parser.add_argument(
        "--preset", default=None, help="Save as named preset in presets/"
    )
    lut_parser.add_argument(
        "--multi-scene", action="store_true",
        help="Generate per-scene LUTs via clustering",
    )

    # --- grade command ---
    grade_parser = subparsers.add_parser(
        "grade", help="Apply an existing .cube LUT or built-in preset to raw footage"
    )
    grade_parser.add_argument(
        "--input", required=True, help="Raw footage video path"
    )
    grade_parser.add_argument(
        "--lut", default=None, help="Path to .cube LUT file"
    )
    grade_parser.add_argument(
        "--preset", default=None, help="Built-in preset name (e.g. cinematic_warm)"
    )
    grade_parser.add_argument(
        "--output", required=True, help="Output graded video path"
    )
    grade_parser.add_argument(
        "--quality", type=int, default=18, help="CRF quality (default: 18)"
    )
    grade_parser.add_argument(
        "--strength", type=float, default=1.0,
        help="Grade strength 0.0-1.0 (default: 1.0)",
    )
    grade_parser.add_argument(
        "--auto-wb", action="store_true",
        help="Auto white balance before grading",
    )
    grade_parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of parallel workers",
    )
    grade_parser.add_argument(
        "--gpu", action="store_true",
        help="Use GPU encoding if available",
    )

    # --- transfer command ---
    transfer_parser = subparsers.add_parser(
        "transfer",
        help="Extract style from reference and apply to raw footage",
    )
    transfer_parser.add_argument(
        "--reference", required=True, help="Reference video path"
    )
    transfer_parser.add_argument(
        "--input", required=True, help="Raw footage video path"
    )
    transfer_parser.add_argument(
        "--output", default=None, help="Output graded video path"
    )
    transfer_parser.add_argument(
        "--preset", default=None, help="Also save LUT as named preset"
    )
    transfer_parser.add_argument(
        "--multi-scene", action="store_true",
        help="Use per-scene LUT clustering",
    )
    transfer_parser.add_argument(
        "--strength", type=float, default=1.0,
        help="Grade strength 0.0-1.0 (default: 1.0)",
    )
    transfer_parser.add_argument(
        "--auto-wb", action="store_true",
        help="Auto white balance before grading",
    )
    transfer_parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of parallel workers",
    )
    transfer_parser.add_argument(
        "--gpu", action="store_true",
        help="Use GPU encoding if available",
    )

    # --- preview command ---
    preview_parser = subparsers.add_parser(
        "preview", help="Show before/after comparison frame"
    )
    preview_parser.add_argument(
        "--reference", required=True, help="Reference video path"
    )
    preview_parser.add_argument(
        "--input", required=True, help="Raw footage video path"
    )
    preview_parser.add_argument(
        "--timestamp", type=float, default=None,
        help="Timestamp in seconds (default: middle of video)",
    )
    preview_parser.add_argument(
        "--output", default="output/preview.png",
        help="Output comparison image path",
    )
    preview_parser.add_argument(
        "--mode", choices=["side_by_side", "slider"], default="side_by_side",
        help="Comparison mode (default: side_by_side)",
    )
    preview_parser.add_argument(
        "--strength", type=float, default=1.0,
        help="Grade strength 0.0-1.0 (default: 1.0)",
    )

    # --- presets command ---
    presets_parser = subparsers.add_parser(
        "presets", help="List or generate built-in presets"
    )
    presets_parser.add_argument(
        "--list", action="store_true", help="List available presets"
    )
    presets_parser.add_argument(
        "--generate", action="store_true",
        help="Generate all built-in preset .cube files",
    )

    # --- smart command ---
    smart_parser = subparsers.add_parser(
        "smart", help="AI Smart Grade — auto-detect mood and apply best preset"
    )
    smart_parser.add_argument(
        "--input", required=True, help="Raw footage video path"
    )
    smart_parser.add_argument(
        "--output", required=True, help="Output graded video path"
    )
    smart_parser.add_argument(
        "--strength", type=float, default=None,
        help="Override strength 0.0-1.0 (default: AI decides)",
    )
    smart_parser.add_argument(
        "--lut-only", action="store_true",
        help="Only analyze and output the recommended LUT (skip video encoding)",
    )

    # --- serve command ---
    serve_parser = subparsers.add_parser(
        "serve",
        help="Launch the full-stack RenderIQ application (backend + frontend)",
    )
    serve_parser.add_argument(
        "--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (default: 8000)"
    )
    serve_parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't auto-open the browser",
    )
    serve_parser.add_argument(
        "--build-frontend", action="store_true",
        help="Force rebuild the frontend before serving",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "lut":
        _cmd_lut(args)
    elif args.command == "grade":
        _cmd_grade(args)
    elif args.command == "transfer":
        _cmd_transfer(args)
    elif args.command == "preview":
        _cmd_preview(args)
    elif args.command == "presets":
        _cmd_presets(args)
    elif args.command == "smart":
        _cmd_smart(args)


def _cmd_lut(args: argparse.Namespace) -> None:
    validation = validate_video(args.reference)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    output_dir = "output/"
    if args.output:
        output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else "."

    result = process(
        reference_path=args.reference,
        lut_only=True,
        output_dir=output_dir,
        preset_name=args.preset,
        multi_scene=args.multi_scene,
    )

    if args.output and result["lut_path"] != args.output:
        import shutil
        shutil.move(result["lut_path"], args.output)
        result["lut_path"] = args.output

    print(f"LUT saved to: {result['lut_path']}")
    if result.get("multi_scene_paths"):
        for p in result["multi_scene_paths"]:
            print(f"  Scene LUT: {p}")
    print(f"Processing time: {result['processing_time']:.1f}s")


def _cmd_grade(args: argparse.Namespace) -> None:
    validation = validate_video(args.input)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    if not args.lut and not args.preset:
        print("Error: Must specify --lut or --preset", file=sys.stderr)
        sys.exit(1)

    if args.preset:
        try:
            lut_path = get_preset_path(args.preset)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        lut = load_cube(lut_path)
    else:
        lut = load_cube(args.lut)

    output = apply_lut_to_video(
        args.input, lut, args.output,
        quality=args.quality,
        strength=args.strength,
        auto_wb=args.auto_wb,
        workers=args.workers,
        use_gpu=args.gpu,
    )
    print(f"Graded video saved to: {output}")


def _cmd_transfer(args: argparse.Namespace) -> None:
    validation = validate_video(args.reference)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: Invalid reference video: {error}", file=sys.stderr)
        sys.exit(1)
    validation = validate_video(args.input)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: Invalid input video: {error}", file=sys.stderr)
        sys.exit(1)

    output_dir = "output/"
    if args.output:
        output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else "output/"

    result = process(
        reference_path=args.reference,
        raw_footage_path=args.input,
        output_dir=output_dir,
        preset_name=args.preset,
        multi_scene=args.multi_scene,
        strength=args.strength,
        auto_wb=args.auto_wb,
        workers=args.workers,
        use_gpu=args.gpu,
    )

    if args.output and result["graded_video_path"] != args.output:
        import shutil
        shutil.move(result["graded_video_path"], args.output)
        result["graded_video_path"] = args.output

    print(f"LUT saved to: {result['lut_path']}")
    print(f"Graded video saved to: {result['graded_video_path']}")
    print(f"Processing time: {result['processing_time']:.1f}s")


def _cmd_preview(args: argparse.Namespace) -> None:
    validation = validate_video(args.reference)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: Invalid reference video: {error}", file=sys.stderr)
        sys.exit(1)
    validation = validate_video(args.input)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: Invalid input video: {error}", file=sys.stderr)
        sys.exit(1)

    # Generate LUT first
    result = process(
        reference_path=args.reference,
        raw_footage_path=args.input,
        lut_only=True,
    )

    lut = load_cube(result["lut_path"])
    original, graded = preview_grade(
        args.input, lut, timestamp=args.timestamp, strength=args.strength
    )

    # Create comparison image
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    comparison = create_comparison(original, graded, mode=args.mode)

    # RGB to BGR for OpenCV save
    cv2.imwrite(args.output, cv2.cvtColor(comparison, cv2.COLOR_RGB2BGR))
    print(f"Preview saved to: {args.output}")


def _cmd_presets(args: argparse.Namespace) -> None:
    if args.generate:
        print("Generating all built-in presets...")
        paths = generate_all_presets()
        for p in paths:
            print(f"  Generated: {p}")
        print(f"Done. {len(paths)} presets generated.")
        return

    # Default: list presets
    presets = list_presets()
    print(f"\nRenderIQ Built-in Presets ({len(presets)} available):")
    print("-" * 50)
    for p in presets:
        status = "ready" if p["exists"] else "not generated"
        print(f"  {p['name']:25s} {p['title']:25s} [{status}]")
    print()
    print("Usage: python cli.py grade --input video.mp4 --preset <name> --output out.mp4")
    print("Generate all: python cli.py presets --generate")


def _cmd_smart(args: argparse.Namespace) -> None:
    validation = validate_video(args.input)
    if validation is not True:
        error = validation.get("error", "Invalid video") if isinstance(validation, dict) else "Invalid video"
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    from renderiq.smart_grade import smart_grade

    lut_out = args.output
    if args.lut_only:
        lut_out = args.output if args.output.endswith(".cube") else args.output + ".cube"

    def progress_cb(step, pct):
        print(f"\r  [{pct:3d}%] {step}", end="", flush=True)

    result = smart_grade(
        video_path=args.input,
        output_path=args.output,
        strength_override=args.strength,
        lut_only=args.lut_only,
        progress_callback=progress_cb,
    )
    print()  # newline after progress

    mood = result["mood_profile"]
    grade = result["grade_applied"]
    print(f"\n  Mood detected:  {mood['mood']}")
    print(f"  Preset applied: {grade['preset']} at {grade['strength']:.0%} strength")
    print(f"  Description:    {grade['description']}")

    if args.lut_only:
        # Export the preset as .cube
        from renderiq.presets_builder import get_preset_path
        preset_path = get_preset_path(grade["preset"])
        shutil.copy2(preset_path, lut_out)
        print(f"\n  LUT saved to:   {lut_out}")
    else:
        print(f"\n  Graded video:   {result['output_path']}")
    print(f"  Processing time: {result['processing_time']:.1f}s")


def _cmd_serve(args: argparse.Namespace) -> None:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    frontend_dist = os.path.join(frontend_dir, "dist")

    # Check system dependencies
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found. Install it first:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt install ffmpeg", file=sys.stderr)
        print("  macOS:         brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    # Build frontend if needed
    if args.build_frontend or not os.path.isdir(frontend_dist):
        if not os.path.isfile(os.path.join(frontend_dir, "package.json")):
            print("Warning: frontend/ not found. Running API-only mode.",
                  file=sys.stderr)
        else:
            npm = shutil.which("npm")
            if not npm:
                print("Warning: npm not found. Skipping frontend build.",
                      file=sys.stderr)
                print("  Install Node.js 18+ for the web UI.", file=sys.stderr)
            else:
                print("Building frontend...")
                node_modules = os.path.join(frontend_dir, "node_modules")
                if not os.path.isdir(node_modules):
                    print("  Installing frontend dependencies...")
                    r = subprocess.run(
                        [npm, "ci"], cwd=frontend_dir,
                        capture_output=True, text=True,
                    )
                    if r.returncode != 0:
                        # npm ci can fail if no lock file; fall back to npm install
                        r = subprocess.run(
                            [npm, "install"], cwd=frontend_dir,
                            capture_output=True, text=True,
                        )
                        if r.returncode != 0:
                            print(f"  npm install failed: {r.stderr[-300:]}", file=sys.stderr)
                            sys.exit(1)

                print("  Compiling frontend assets...")
                r = subprocess.run(
                    [npm, "run", "build"], cwd=frontend_dir,
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print(f"  Build failed: {r.stderr[-300:]}", file=sys.stderr)
                    sys.exit(1)
                print("  Frontend built successfully.")

    # Generate presets if needed
    from renderiq.presets_builder import PRESETS_DIR
    if not os.path.isdir(PRESETS_DIR) or len(os.listdir(PRESETS_DIR)) < 10:
        print("Generating built-in presets...")
        generate_all_presets()

    # Create working directories
    for d in ["uploads", "jobs", "output"]:
        os.makedirs(os.path.join(root_dir, d), exist_ok=True)

    host = args.host
    port = args.port
    display_host = "localhost" if host == "0.0.0.0" else host
    url = f"http://{display_host}:{port}"

    print(f"""
╔══════════════════════════════════════════╗
║          RenderIQ v1.0.0                 ║
║   AI Color Grade Transfer Tool           ║
╠══════════════════════════════════════════╣
║                                          ║
║   App running at: {url:<21s} ║
║   API docs:       {url + '/api/docs':<21s} ║
║                                          ║
║   Press Ctrl+C to stop                   ║
╚══════════════════════════════════════════╝
""")

    # Open browser
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # Launch uvicorn
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
