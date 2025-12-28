#!/bin/bash
# LedgerLoop CoreLab Deployment Script
# Usage: ./scripts/deploy-corelab.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== LedgerLoop CoreLab Deployment ==="
echo "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Check for .env file
if [ ! -f .env ]; then
    if [ -f .env.corelab ]; then
        echo "Creating .env from .env.corelab template..."
        cp .env.corelab .env
        echo "WARNING: Please edit .env and set KASHAT_JWT_SECRET before continuing!"
        echo "Generate a secret with: openssl rand -base64 32"
        exit 1
    else
        echo "ERROR: No .env file found. Copy .env.corelab to .env and configure it."
        exit 1
    fi
fi

# Check JWT secret is set
if grep -q "CHANGE_ME" .env 2>/dev/null; then
    echo "ERROR: KASHAT_JWT_SECRET is not configured in .env"
    echo "Generate a secret with: openssl rand -base64 32"
    exit 1
fi

# Create data directories
echo "Creating data directories..."
sudo mkdir -p /opt/kashat/data
sudo mkdir -p /opt/kashat/backups
sudo chown -R 1000:1000 /opt/kashat

# Stop existing containers
echo "Stopping existing containers..."
docker compose -f docker-compose.corelab.yml down 2>/dev/null || true

# Build and start
echo "Building containers..."
docker compose -f docker-compose.corelab.yml build

echo "Starting containers..."
docker compose -f docker-compose.corelab.yml up -d

# Wait for health
echo "Waiting for services to become healthy..."
sleep 10

# Run health check
./scripts/health-check.sh

echo ""
echo "=== Deployment Complete ==="
echo "Access LedgerLoop at: http://kashat.lab-core.local"
echo "or: http://lab-core.local:3000"
