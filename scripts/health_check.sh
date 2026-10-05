#!/usr/bin/env bash
# ==============================================================================
# Script: health_check.sh
# Purpose: Probe the /health endpoint and return exit status for automation/CI
# ==============================================================================

set -euo pipefail

TARGET_HOST="${HOST:-127.0.0.1}"
TARGET_PORT="${PORT:-5000}"
HEALTH_URL="http://${TARGET_HOST}:${TARGET_PORT}/health"
MAX_ATTEMPTS=10
RETRY_DELAY=2

echo "[INFO] Running health check against: ${HEALTH_URL}"

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "[ATTEMPT $i/$MAX_ATTEMPTS] Probing ${HEALTH_URL}..."
    
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${HEALTH_URL}" || true)
    HTTP_BODY=$(echo "${RESPONSE}" | sed -e '$d')
    HTTP_STATUS=$(echo "${RESPONSE}" | grep "HTTP_STATUS" | cut -d':' -f2)

    if [ "${HTTP_STATUS}" = "200" ]; then
        echo "[SUCCESS] Service is healthy!"
        echo "[RESPONSE] ${HTTP_BODY}"
        exit 0
    else
        echo "[WARN] Status code: ${HTTP_STATUS}. Retrying in ${RETRY_DELAY} seconds..."
        sleep ${RETRY_DELAY}
    fi
done

echo "[ERROR] Health check failed after ${MAX_ATTEMPTS} attempts."
exit 1
