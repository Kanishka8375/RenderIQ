#!/bin/bash

echo "=== RenderIQ Health Check ==="

# Check backend
echo -n "Backend API: "
HEALTH=$(curl -s http://localhost:8000/api/health)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "OK - Running"
else
    echo "FAIL - DOWN"
    exit 1
fi

# Check frontend
echo -n "Frontend:    "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ "$HTTP_CODE" = "200" ]; then
    echo "OK - Running"
else
    echo "FAIL - DOWN (HTTP $HTTP_CODE)"
    exit 1
fi

# Check presets
echo -n "Presets:     "
PRESETS=$(curl -s http://localhost:8000/api/presets)
if echo "$PRESETS" | grep -q '"presets"'; then
    echo "OK - Loaded"
else
    echo "FAIL - Missing"
    exit 1
fi

# Check disk space
echo -n "Disk Space:  "
FREE=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "$FREE" -gt 5 ]; then
    echo "OK - ${FREE}GB free"
else
    echo "WARN - Low: ${FREE}GB free"
fi

echo ""
echo "=== All checks passed ==="
