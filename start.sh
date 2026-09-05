#!/usr/bin/env bash

# ============================================================
# SIH26056 — Airfare CPI Launch Script
# Starts a migration-verified FastAPI backend + Next.js frontend.
# ============================================================

set -Eeuo pipefail

# Get project root directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

BACKEND_LOG="/tmp/airfare_backend.log"
FRONTEND_LOG="/tmp/airfare_frontend.log"
MIGRATION_LOG="/tmp/airfare_migration.log"
BACKEND_PID=""
FRONTEND_PID=""
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [[ -x "$DIR/backend/.venv/bin/python" ]]; then
    PYTHON_BIN="$DIR/backend/.venv/bin/python"
else
    PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    echo "❌ Python 3 was not found. Install Python and the backend requirements first."
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import alembic, uvicorn' > /dev/null 2>&1; then
    echo "❌ Backend dependencies are missing for $PYTHON_BIN."
    echo "   Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if ! command -v npm > /dev/null 2>&1; then
    echo "❌ npm was not found. Install Node.js and run npm install in frontend/."
    exit 1
fi

require_free_port() {
    local port="$1"
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN > /dev/null 2>&1; then
        echo "❌ Port $port is already in use. Stop that service or choose another port (e.g. FRONTEND_PORT=3001 ./start.sh):"
        lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
        exit 1
    fi
}

echo "============================================================"
echo "🛫 Starting SIH26056: Real-Time Airfare CPI for MoSPI"
echo "============================================================"

echo "🔎 [0/4] Checking ports $BACKEND_PORT and $FRONTEND_PORT..."
require_free_port "$BACKEND_PORT"
require_free_port "$FRONTEND_PORT"

# Only processes started by this invocation are stopped. Never kill an unrelated
# process simply because it happens to use one of the development ports.
cleanup() {
    local status=$?
    trap - EXIT SIGINT SIGTERM
    echo ""
    echo "🛬 Shutting down Airfare CPI services..."
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "✅ All services stopped."
    exit "$status"
}

trap cleanup SIGINT SIGTERM EXIT

# Create or update only the database configured for this run. The initial
# migration refuses an existing unversioned schema, so the legacy data file is
# protected instead of being guessed at, relabelled, or overwritten.
echo "🗃️  [1/4] Verifying the versioned database schema..."
cd "$DIR/backend"
if ! "$PYTHON_BIN" -c 'from alembic.config import main; main()' -c alembic.ini upgrade head > "$MIGRATION_LOG" 2>&1; then
    echo "❌ Database migration failed. The backend was not started."
    echo "   Existing legacy data is preserved; inspect $MIGRATION_LOG."
    tail -n 40 "$MIGRATION_LOG" || true
    exit 1
fi
echo "   ✅ Database schema is ready."

# 1. Start Backend API
echo "⚙️  [2/4] Starting Backend API on http://localhost:$BACKEND_PORT..."
"$PYTHON_BIN" -m uvicorn api.main:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "   ↳ Backend running (PID: $BACKEND_PID, logs: $BACKEND_LOG)"

# Wait for backend to report healthy, but expose a fatal startup failure as soon
# as Uvicorn writes it instead of hiding the cause behind a blind polling loop.
echo "⏳ Waiting for backend initialization..."
BACKEND_READY=false
for i in $(seq 1 30); do
    if curl --silent --fail --max-time 2 "http://localhost:$BACKEND_PORT/api/v1/health" > /dev/null; then
        echo "   ✅ Backend is ready!"
        BACKEND_READY=true
        break
    fi
    if [[ -f "$BACKEND_LOG" ]] && rg -q "Application startup failed|Traceback \(most recent call last\)" "$BACKEND_LOG"; then
        echo "❌ Backend startup failed. Last log lines:"
        tail -n 60 "$BACKEND_LOG" || true
        exit 1
    fi
    sleep 1
done

if [[ "$BACKEND_READY" != "true" ]]; then
    echo "❌ Backend did not become healthy within 30 seconds. Last log lines:"
    tail -n 60 "$BACKEND_LOG" || true
    exit 1
fi

# 2. Start Frontend Dashboard
echo "🎨 [3/4] Starting Next.js Dashboard on http://localhost:$FRONTEND_PORT..."
cd "$DIR/frontend"
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}" npm run dev -- -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "   ↳ Frontend running (PID: $FRONTEND_PID, logs: $FRONTEND_LOG)"

# Wait for frontend to respond
echo "⏳ Waiting for frontend initialization..."
FRONTEND_READY=false
for i in $(seq 1 30); do
    HTTP_CODE=$(curl --silent --output /dev/null --write-out "%{http_code}" --max-time 2 "http://localhost:$FRONTEND_PORT" 2>/dev/null || true)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ Frontend is ready!"
        FRONTEND_READY=true
        break
    fi
    sleep 1
done

if [[ "$FRONTEND_READY" != "true" ]]; then
    echo "❌ Frontend did not become ready within 30 seconds. Last log lines:"
    tail -n 60 "$FRONTEND_LOG" || true
    exit 1
fi

echo ""
echo "============================================================"
echo "✨ Airfare CPI System is LIVE!"
echo "   📊 Dashboard:    http://localhost:$FRONTEND_PORT"
echo "   📖 API Docs:     http://localhost:$BACKEND_PORT/docs"
echo "   🏛️ MoSPI Report: http://localhost:$BACKEND_PORT/api/v1/reports/monthly/html"
echo "============================================================"

# Set OPEN_BROWSER=false for an unattended/local smoke test.
if [[ "${OPEN_BROWSER:-true}" == "true" ]]; then
    echo "🚀 Opening http://localhost:$FRONTEND_PORT in your default browser..."
    # Open default browser (macOS / Linux / Windows WSL)
    if [[ "${OSTYPE:-}" == "darwin"* ]]; then
        open "http://localhost:$FRONTEND_PORT"
    elif [[ "${OSTYPE:-}" == "linux-gnu"* ]] && command -v xdg-open > /dev/null 2>&1; then
        xdg-open "http://localhost:$FRONTEND_PORT"
    fi
else
    echo "ℹ️  Browser launch skipped (OPEN_BROWSER=false)."
fi

echo ""
echo "Press Ctrl+C in this terminal to stop all services."
echo ""

# Keep running and wait for background processes
while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Backend stopped unexpectedly. Last log lines:"
        tail -n 60 "$BACKEND_LOG" || true
        exit 1
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "❌ Frontend stopped unexpectedly. Last log lines:"
        tail -n 60 "$FRONTEND_LOG" || true
        exit 1
    fi
    sleep 1
done
