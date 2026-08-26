#!/bin/bash

# ============================================================
# SIH26056 — Airfare CPI Launch Script
# Starts FastAPI backend + Next.js frontend and opens browser
# ============================================================

# Do not exit immediately on non-critical command failures
set +e

# Get project root directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================================"
echo "🛫 Starting SIH26056: Real-Time Airfare CPI for MoSPI"
echo "============================================================"

# Pre-cleanup any stale processes on port 8000 and 3000
echo "🧹 [0/3] Clearing ports 8000 and 3000..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Function to clean up background processes on Ctrl+C / exit
cleanup() {
    echo ""
    echo "🛬 Shutting down Airfare CPI services..."
    if [ -n "$BACKEND_PID" ]; then
        kill -9 "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill -9 "$FRONTEND_PID" 2>/dev/null || true
    fi
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    echo "✅ All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend API
echo "⚙️  [1/3] Starting Backend API on http://localhost:8000..."
cd "$DIR/backend"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/airfare_backend.log 2>&1 &
BACKEND_PID=$!
echo "   ↳ Backend running (PID: $BACKEND_PID, logs: /tmp/airfare_backend.log)"

# Wait for backend to report healthy
echo "⏳ Waiting for backend initialization..."
for i in {1..30}; do
    if curl -s -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "   ✅ Backend is ready!"
        break
    fi
    sleep 1
done

# 2. Start Frontend Dashboard
echo "🎨 [2/3] Starting Next.js Dashboard on http://localhost:3000..."
cd "$DIR/frontend"
npm run dev -- -p 3000 > /tmp/airfare_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   ↳ Frontend running (PID: $FRONTEND_PID, logs: /tmp/airfare_frontend.log)"

# Wait for frontend to respond
echo "⏳ Waiting for frontend initialization..."
for i in {1..30}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ Frontend is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "============================================================"
echo "✨ Airfare CPI System is LIVE!"
echo "   📊 Dashboard:    http://localhost:3000"
echo "   📖 API Docs:     http://localhost:8000/docs"
echo "   🏛️ MoSPI Report: http://localhost:8000/api/v1/reports/monthly/html"
echo "============================================================"
echo "🚀 Opening http://localhost:3000 in your default browser..."

# Open default browser (macOS / Linux / Windows WSL)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:3000"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if which xdg-open > /dev/null 2>&1; then
        xdg-open "http://localhost:3000"
    fi
fi

echo ""
echo "Press Ctrl+C in this terminal to stop all services."
echo ""

# Keep running and wait for background processes
while true; do
    sleep 1
done
