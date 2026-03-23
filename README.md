# RenderIQ

AI-powered color grading. Upload your footage, pick a style, download.

## What it does

RenderIQ extracts the color grading style from any reference video and applies it to your footage. Pick from 10 built-in cinematic presets or upload your own reference. Get a graded video or a .cube LUT file for your editing software.

## Quick Start

**Try it online:** [renderiq.in](https://renderiq.in)

**Run locally with Docker:**

```bash
docker-compose up -d
# Visit http://localhost
```

**Run without Docker:**

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend && npm install && npm run dev
```

FFmpeg must be installed system-wide:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## CLI Usage

```bash
# Generate LUT from reference video
python cli.py lut --reference movie_clip.mp4 --output presets/cinematic.cube

# Apply existing LUT to raw footage
python cli.py grade --input raw_footage.mp4 --lut presets/cinematic.cube --output output/graded.mp4

# Full pipeline: extract style + apply
python cli.py transfer --reference movie_clip.mp4 --input raw_footage.mp4 --output output/graded.mp4

# Apply a built-in preset
python cli.py preset --name cinematic_warm --input raw_footage.mp4 --output output/graded.mp4

# Preview before/after comparison
python cli.py preview --reference movie_clip.mp4 --input raw_footage.mp4 --timestamp 10.5
```

## Features

- 10 built-in cinematic presets (warm, cold, teal & orange, vintage, B&W, moody, pastel, neon, golden hour, anime)
- Custom reference video style matching
- Adjustable grade strength (0-100%)
- Multi-scene intelligent grading
- Auto white balance correction
- Export as video (MP4) or LUT (.cube file)
- Works with DaVinci Resolve, Premiere Pro, Final Cut Pro
- Web app with drag-and-drop upload and real-time progress
- Before/after comparison slider
- Background job processing with queue management

## Tech Stack

- **Backend:** Python, FastAPI, OpenCV, FFmpeg
- **Frontend:** React, Vite, Tailwind CSS
- **Color Science:** LAB color space, 3D LUT interpolation, histogram matching
- **Deployment:** Docker, Nginx

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload/raw` | Upload raw footage |
| POST | `/api/upload/reference` | Upload reference video |
| GET | `/api/presets` | List available presets |
| GET | `/api/presets/{name}/preview` | Preview a preset |
| POST | `/api/grade/start` | Start grading job |
| GET | `/api/grade/status/{job_id}` | Check job progress |
| GET | `/api/download/{job_id}/video` | Download graded video |
| GET | `/api/download/{job_id}/lut` | Download .cube LUT |
| GET | `/api/health` | Health check |

## Running Tests

```bash
# All tests
pytest tests/ -v

# Frontend tests
cd frontend && npm test
```

## Project Structure

```
renderiq/           Core engine (sampler, analyzer, LUT generator, grader)
backend/            FastAPI web server (routes, services, models)
frontend/           React + Tailwind web app
presets/            Built-in .cube LUT files
scripts/            Demo generation utilities
tests/              Test suite (90+ tests)
Dockerfile          Backend container
docker-compose.yml  Full stack deployment
```

## License

MIT
