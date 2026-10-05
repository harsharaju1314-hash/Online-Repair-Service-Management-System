#!/usr/bin/env bash
# ==============================================================================
# Script: start.sh
# Purpose: Start the Flask application locally or in a background process
# ==============================================================================

set -euo pipefail

APP_PORT="${PORT:-5000}"
APP_HOST="${HOST:-0.0.0.0}"
APP_ENV="${FLASK_ENV:-development}"

echo "[INFO] Starting Online Repair Service Management System..."
echo "[INFO] Environment: ${APP_ENV}"
echo "[INFO] Host: ${APP_HOST} | Port: ${APP_PORT}"

# Export environment variables if .env file exists
if [ -f .env ]; then
    echo "[INFO] Loading configuration from .env file"
    export $(grep -v '^#' .env | xargs)
fi

export FLASK_ENV="${APP_ENV}"
export PORT="${APP_PORT}"
export HOST="${APP_HOST}"

# Execute application
python run.py
