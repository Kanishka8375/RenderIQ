#!/usr/bin/env bash
# RenderIQ launcher — auto-activates venv if needed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi
exec python3 "$SCRIPT_DIR/cli.py" "$@"
