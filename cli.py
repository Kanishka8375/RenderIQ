"""Command-line interface for RenderIQ."""

import argparse
import logging
import sys

import cv2
import numpy as np

from renderiq.pipeline import process
from renderiq.lut_generator import load_cube
from renderiq.grader import apply_lut_to_video, preview_grade
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

    # --- grade command ---
    grade_parser = subparsers.add_parser(
        "grade", help="Apply an existing .cube LUT to raw footage"
    )
    grade_parser.add_argument(
        "--input", required=True, help="Raw footage video path"
    )
    grade_parser.add_argument(
        "--lut", required=True, help="Path to .cube LUT file"
    )
    grade_parser.add_argument(
        "--output", required=True, help="Output graded video path"
    )
    grade_parser.add_argument(
        "--quality", type=int, default=18, help="CRF quality (default: 18)"
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

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "lut":
        _cmd_lut(args)
    elif args.command == "grade":
        _cmd_grade(args)
    elif args.command == "transfer":
        _cmd_transfer(args)
    elif args.command == "preview":
        _cmd_preview(args)


def _cmd_lut(args: argparse.Namespace) -> None:
    if not validate_video(args.reference):
        print(f"Error: Invalid video file: {args.reference}", file=sys.stderr)
        sys.exit(1)

    output_dir = "output/"
    if args.output:
        output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else "."

    result = process(
        reference_path=args.reference,
        lut_only=True,
        output_dir=output_dir,
        preset_name=args.preset,
    )

    if args.output and result["lut_path"] != args.output:
        import shutil
        shutil.move(result["lut_path"], args.output)
        result["lut_path"] = args.output

    print(f"LUT saved to: {result['lut_path']}")
    print(f"Processing time: {result['processing_time']:.1f}s")


def _cmd_grade(args: argparse.Namespace) -> None:
    if not validate_video(args.input):
        print(f"Error: Invalid video file: {args.input}", file=sys.stderr)
        sys.exit(1)

    lut = load_cube(args.lut)
    output = apply_lut_to_video(args.input, lut, args.output, quality=args.quality)
    print(f"Graded video saved to: {output}")


def _cmd_transfer(args: argparse.Namespace) -> None:
    if not validate_video(args.reference):
        print(f"Error: Invalid reference video: {args.reference}", file=sys.stderr)
        sys.exit(1)
    if not validate_video(args.input):
        print(f"Error: Invalid input video: {args.input}", file=sys.stderr)
        sys.exit(1)

    output_dir = "output/"
    if args.output:
        output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else "output/"

    result = process(
        reference_path=args.reference,
        raw_footage_path=args.input,
        output_dir=output_dir,
        preset_name=args.preset,
    )

    if args.output and result["graded_video_path"] != args.output:
        import shutil
        shutil.move(result["graded_video_path"], args.output)
        result["graded_video_path"] = args.output

    print(f"LUT saved to: {result['lut_path']}")
    print(f"Graded video saved to: {result['graded_video_path']}")
    print(f"Processing time: {result['processing_time']:.1f}s")


def _cmd_preview(args: argparse.Namespace) -> None:
    if not validate_video(args.reference):
        print(f"Error: Invalid reference video: {args.reference}", file=sys.stderr)
        sys.exit(1)
    if not validate_video(args.input):
        print(f"Error: Invalid input video: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Generate LUT first
    result = process(
        reference_path=args.reference,
        raw_footage_path=args.input,
        lut_only=True,
    )

    lut = load_cube(result["lut_path"])
    original, graded = preview_grade(args.input, lut, timestamp=args.timestamp)

    # Create side-by-side comparison
    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    comparison = np.hstack([original, graded])
    # RGB to BGR for OpenCV save
    cv2.imwrite(args.output, cv2.cvtColor(comparison, cv2.COLOR_RGB2BGR))
    print(f"Preview saved to: {args.output}")


if __name__ == "__main__":
    main()
