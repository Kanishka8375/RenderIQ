"""Vercel serverless entrypoint for RenderIQ FastAPI backend."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
