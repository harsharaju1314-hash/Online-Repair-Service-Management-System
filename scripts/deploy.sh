#!/usr/bin/env bash
# ==============================================================================
# Script: deploy.sh
# Purpose: Staging deployment workflow script (Build -> Deploy -> Health Check)
# ==============================================================================

set -euo pipefail

IMAGE_NAME="online-repair-service"
IMAGE_TAG="staging"
CONTAINER_NAME="repair-service-staging"
STAGING_PORT="5000"

echo "=================================================="
echo " Starting Staging Deployment: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "=================================================="

# 1. Run Tests prior to deployment
echo "[STEP 1/4] Running automated test suite with pytest..."
pytest -v || {
    echo "[FAIL] Pytest tests failed! Aborting staging deployment."
    exit 1
}

# 2. Build Container Image
echo "[STEP 2/4] Building Docker container image..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

# 3. Stop and remove existing container if running
echo "[STEP 3/4] Re-deploying staging container..."
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "[INFO] Stopping old container ${CONTAINER_NAME}..."
    docker stop "${CONTAINER_NAME}" || true
    docker rm "${CONTAINER_NAME}" || true
fi

docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${STAGING_PORT}:5000" \
    -e FLASK_ENV=production \
    -e SECRET_KEY="${SECRET_KEY:-staging-secret-key-123}" \
    "${IMAGE_NAME}:${IMAGE_TAG}"

# 4. Perform Health Check Verification
echo "[STEP 4/4] Verifying staging deployment health..."
sleep 3
HOST="127.0.0.1" PORT="${STAGING_PORT}" bash scripts/health_check.sh

echo "=================================================="
echo " Staging Deployment Successful on http://127.0.0.1:${STAGING_PORT}"
echo "=================================================="
