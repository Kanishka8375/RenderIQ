# RenderIQ — AI Color Grade Transfer Tool

Extract color grading styles from reference videos and apply them to raw footage.

## Quick Start

```bash
pip install -r requirements.txt
```

FFmpeg must be installed system-wide:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Usage

```bash
# Generate LUT from reference video
python cli.py lut --reference movie_clip.mp4 --output presets/cinematic.cube

# Apply existing LUT to raw footage
python cli.py grade --input raw_footage.mp4 --lut presets/cinematic.cube --output output/graded.mp4

# Full pipeline: extract style + apply
python cli.py transfer --reference movie_clip.mp4 --input raw_footage.mp4 --output output/graded.mp4

# Preview before/after comparison
python cli.py preview --reference movie_clip.mp4 --input raw_footage.mp4 --timestamp 10.5
```

## Running Tests

```bash
pytest tests/ -v
```
