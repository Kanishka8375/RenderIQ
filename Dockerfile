FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY renderiq/ renderiq/
COPY backend/ backend/
COPY presets/ presets/
COPY cli.py .

# Create non-root user and working directories
RUN useradd -m appuser && \
    mkdir -p uploads jobs output && \
    chown -R appuser:appuser /app

# Generate built-in presets
RUN python -c "from renderiq.presets_builder import generate_all_presets; generate_all_presets()"
RUN chown -R appuser:appuser /app/presets

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
