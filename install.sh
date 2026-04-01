#!/usr/bin/env bash
# RenderIQ — Single command install & launch
# Usage: curl -sSL <url>/install.sh | bash
#    or: chmod +x install.sh && ./install.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[RenderIQ]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─── Check system deps ────────────────────────────────────────────────────────
log "Checking system dependencies..."

# Python 3.10+
if ! command -v python3 &>/dev/null; then
    err "Python 3.10+ is required. Install it first:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS:         brew install python@3.12"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    err "Python 3.10+ required (found $PY_VERSION)"
    exit 1
fi
log "  Python $PY_VERSION ✓"

# FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    warn "FFmpeg not found. Attempting to install..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg libsndfile1
    elif command -v brew &>/dev/null; then
        brew install ffmpeg libsndfile
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y ffmpeg libsndfile
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm ffmpeg libsndfile
    else
        err "Cannot auto-install FFmpeg. Please install manually."
        exit 1
    fi
fi
log "  FFmpeg $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}') ✓"

# Node.js (optional but needed for web UI)
HAS_NODE=false
if command -v node &>/dev/null && command -v npm &>/dev/null; then
    NODE_VERSION=$(node --version)
    log "  Node.js $NODE_VERSION ✓"
    HAS_NODE=true
else
    warn "Node.js not found. Web UI will be built on first 'renderiq serve'."
    echo "  Install Node.js 18+: https://nodejs.org/"
fi

# ─── Set up project ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "Installing Python dependencies..."

# Create venv if not in one already
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    log "  Using virtual environment: .venv"
fi

# Install package in editable mode
pip install -e ".[dev]" --quiet 2>&1 | tail -5

log "  Python packages installed ✓"

# ─── Build frontend ──────────────────────────────────────────────────────────
if [ "$HAS_NODE" = true ] && [ -f "frontend/package.json" ]; then
    log "Building frontend..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm ci --silent 2>/dev/null || npm install --silent
    fi
    npm run build --silent
    cd ..
    log "  Frontend built ✓"
fi

# ─── Generate presets ─────────────────────────────────────────────────────────
log "Generating built-in presets..."
python3 -c "from renderiq.presets_builder import generate_all_presets; generate_all_presets()" 2>/dev/null
log "  10 presets generated ✓"

# ─── Create working directories ──────────────────────────────────────────────
mkdir -p uploads jobs output

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  ${GREEN}RenderIQ installed successfully!${CYAN}               ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║                                                  ║${NC}"
echo -e "${CYAN}║${NC}  Launch the full app:                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${GREEN}renderiq serve${NC}                                 ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  CLI commands:                                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${GREEN}renderiq smart${NC}  --input v.mp4 --output out.mp4 ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${GREEN}renderiq grade${NC}  --input v.mp4 --preset ...     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    ${GREEN}renderiq presets${NC} --list                        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
if [ -z "${VIRTUAL_ENV:-}" ]; then
echo -e "${CYAN}║${NC}  ${YELLOW}Activate venv first: source .venv/bin/activate${NC}  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                  ${CYAN}║${NC}"
fi
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
