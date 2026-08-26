#!/bin/bash

# ============================================================
# SIH26056 — Airfare CPI Launch Script
# Starts FastAPI backend + Next.js frontend and opens browser
# ============================================================

set -e

# Get project root directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================================"
echo "🛫 Starting SIH26056: Real-Time Airfare CPI for MoSPI"
echo "============================================================"

# Function to clean up background processes on Ctrl+C / exit
cleanup() {
    echo ""
    echo "🛬 Shutting down Airfare CPI services..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
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

# 2. Start Frontend Dashboard
echo "🎨 [2/3] Starting Next.js Dashboard on http://localhost:3000..."
cd "$DIR/frontend"
npm run dev -- -p 3000 > /tmp/airfare_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   ↳ Frontend running (PID: $FRONTEND_PID, logs: /tmp/airfare_frontend.log)"

# 3. Wait for services to be ready
echo "⏳ [3/3] Waiting for services to initialize..."
MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1 && curl -s http://localhost:3000 > /dev/null 2>&1; then
        break
    fi
    sleep 1
    RETRY=$((RETRY+1))
done

echo ""
echo "============================================================"
echo "✨ System is ready!"
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
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for processes
wait
