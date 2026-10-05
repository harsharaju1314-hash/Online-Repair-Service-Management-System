#!/usr/bin/env bash
# ==============================================================================
# Script: stop.sh
# Purpose: Gracefully stop running Flask / Gunicorn instances on port 5000
# ==============================================================================

set -euo pipefail

APP_PORT="${PORT:-5000}"

echo "[INFO] Searching for processes running on port ${APP_PORT}..."

# Find PID using lsof or fuser
if command -v lsof >/dev/null 2>&1; then
    PID=$(lsof -ti :${APP_PORT} || true)
    if [ -n "${PID}" ]; then
        echo "[INFO] Stopping process PID: ${PID}"
        kill -15 ${PID} || kill -9 ${PID}
        echo "[INFO] Application stopped successfully."
    else
        echo "[INFO] No process found listening on port ${APP_PORT}."
    fi
elif command -v fuser >/dev/null 2>&1; then
    fuser -k "${APP_PORT}/tcp" || echo "[INFO] No process listening on port ${APP_PORT}."
else
    echo "[WARN] Neither lsof nor fuser found. Attempting pkill for python run.py..."
    pkill -f "python run.py" || true
    echo "[INFO] Stop signal sent."
fi
