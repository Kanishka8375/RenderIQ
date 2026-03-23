#!/bin/bash
set -e

echo "=== RenderIQ Deployment ==="

# Step 1: Run tests
echo "[1/5] Running tests..."
python -m pytest tests/ -v --timeout=300
if [ $? -ne 0 ]; then
    echo "TESTS FAILED — aborting deployment"
    exit 1
fi

# Step 2: Build frontend
echo "[2/5] Building frontend..."
cd frontend
npm ci
npm run build
cd ..

# Step 3: Generate presets if missing
echo "[3/5] Generating presets..."
python -c "
from renderiq.presets_builder import generate_all_presets
generate_all_presets()
print('Presets generated successfully')
"

# Step 4: Build Docker images
echo "[4/5] Building Docker images..."
docker-compose build --no-cache

# Step 5: Start services
echo "[5/5] Starting services..."
docker-compose up -d

echo ""
echo "=== Deployment Complete ==="
echo "Frontend: http://localhost (or your domain)"
echo "Backend:  http://localhost:8000"
echo "Health:   http://localhost:8000/health"
echo ""
echo "Verify: curl http://localhost:8000/api/health"
