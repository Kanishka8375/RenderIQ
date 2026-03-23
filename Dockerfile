FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY renderiq/ renderiq/
COPY backend/ backend/
COPY presets/ presets/
COPY cli.py .

# Create working directories
RUN mkdir -p uploads jobs output

# Generate built-in presets
RUN python -c "from renderiq.presets_builder import generate_all_presets; generate_all_presets()"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
