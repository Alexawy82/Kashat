# Phase 4: CoreLab Deployment Configuration

## Your Role
You are a DevOps engineer configuring LedgerLoop for production deployment on CoreLab home server.

## Context
- Target: CoreLab home server at `lab-core.local`
- Infrastructure: Docker on mini PC
- Services: Portainer, Dashy, Traefik (already running)
- Network: Home LAN, not internet-exposed
- Database: DuckDB (file-based, needs persistence)

## Tasks

### 1. Create Production Docker Compose

Create `docker-compose.corelab.yml`:

```yaml
version: '3.8'

services:
  ledgerloop-backend:
    image: ledgerloop-backend:latest
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ledgerloop-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - LEDGERLOOP_ENV=production
      - LEDGERLOOP_LOG_LEVEL=INFO
      - LEDGERLOOP_DATA_DIR=/data
      - LEDGERLOOP_CORS=http://ledgerloop.lab-core.local,http://localhost:3000
      - PYTHONUNBUFFERED=1
    volumes:
      - ledgerloop-data:/data
      - ./bank:/app/bank:ro  # Read-only access to bank statements
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/live')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - ledgerloop-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ledgerloop-api.rule=Host(`ledgerloop-api.lab-core.local`)"
      - "traefik.http.services.ledgerloop-api.loadbalancer.server.port=8000"

  ledgerloop-web:
    image: ledgerloop-web:latest
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: ledgerloop-web
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://ledgerloop-api.lab-core.local
      - HOSTNAME=0.0.0.0
    depends_on:
      ledgerloop-backend:
        condition: service_healthy
    networks:
      - ledgerloop-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ledgerloop.rule=Host(`ledgerloop.lab-core.local`)"
      - "traefik.http.services.ledgerloop.loadbalancer.server.port=3000"

volumes:
  ledgerloop-data:
    driver: local

networks:
  ledgerloop-net:
    driver: bridge
```

### 2. Create Production Environment File

Create `.env.corelab`:

```bash
# LedgerLoop CoreLab Production Configuration

# Backend
LEDGERLOOP_ENV=production
LEDGERLOOP_LOG_LEVEL=INFO
LEDGERLOOP_DATA_DIR=/data
LEDGERLOOP_CORS=http://ledgerloop.lab-core.local,http://localhost:3000

# Frontend
NODE_ENV=production
NEXT_PUBLIC_API_URL=http://ledgerloop-api.lab-core.local

# Optional: OpenAI for AI features (leave blank to disable)
OPENAI_API_KEY=

# Database is DuckDB file at /data/ledgerloop.duckdb
# No separate DB configuration needed
```

### 3. Create Deployment Script

Create `scripts/deploy-corelab.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Deploying LedgerLoop to CoreLab..."

# Configuration
COMPOSE_FILE="docker-compose.corelab.yml"
ENV_FILE=".env.corelab"

# Check prerequisites
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Missing $COMPOSE_FILE"
    exit 1
fi

# Stop existing containers
echo "📦 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down || true

# Build fresh images
echo "🔨 Building images..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Start services
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d

# Wait for health check
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Verify deployment
echo "✅ Verifying deployment..."
curl -sf http://localhost:8000/api/health || { echo "❌ Backend health check failed"; exit 1; }
curl -sf http://localhost:3000 || { echo "❌ Frontend health check failed"; exit 1; }

echo ""
echo "✅ Deployment successful!"
echo ""
echo "📍 Access points:"
echo "   Frontend: http://ledgerloop.lab-core.local"
echo "   Backend:  http://ledgerloop-api.lab-core.local"
echo "   Local:    http://localhost:3000"
echo ""
echo "📊 Container status:"
docker-compose -f $COMPOSE_FILE ps
```

### 4. Create Backup Script

Create `scripts/backup-data.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ledgerloop_$DATE.tar.gz"

mkdir -p $BACKUP_DIR

echo "📦 Creating backup..."

# Get the data volume location
VOLUME_PATH=$(docker volume inspect ledgerloop-data --format '{{ .Mountpoint }}' 2>/dev/null || echo "")

if [ -z "$VOLUME_PATH" ]; then
    # Volume doesn't exist yet, backup from container
    docker cp ledgerloop-backend:/data - | gzip > $BACKUP_FILE
else
    # Backup from volume directly (requires root or docker group)
    tar -czf $BACKUP_FILE -C $VOLUME_PATH .
fi

echo "✅ Backup created: $BACKUP_FILE"

# Keep only last 10 backups
ls -t $BACKUP_DIR/ledgerloop_*.tar.gz | tail -n +11 | xargs -r rm

echo "📊 Available backups:"
ls -lh $BACKUP_DIR/ledgerloop_*.tar.gz
```

### 5. Create Restore Script

Create `scripts/restore-data.sh`:

```bash
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/ledgerloop_*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will overwrite current data!"
read -p "Continue? (y/N) " confirm
if [ "$confirm" != "y" ]; then
    echo "Cancelled"
    exit 0
fi

echo "📦 Restoring from $BACKUP_FILE..."

# Stop backend to release DB lock
docker-compose -f docker-compose.corelab.yml stop ledgerloop-backend

# Restore data
docker run --rm -v ledgerloop-data:/data -v $(pwd):/backup alpine \
    tar -xzf /backup/$BACKUP_FILE -C /data

# Restart backend
docker-compose -f docker-compose.corelab.yml start ledgerloop-backend

echo "✅ Restore complete!"
```

### 6. Update Traefik Labels (if using Traefik)

If CoreLab uses Traefik, ensure these labels are in docker-compose:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.ledgerloop.rule=Host(`ledgerloop.lab-core.local`)"
  - "traefik.http.routers.ledgerloop.entrypoints=web"
  - "traefik.http.services.ledgerloop.loadbalancer.server.port=3000"
```

### 7. DNS/Hosts Configuration

Add to CoreLab's DNS or `/etc/hosts`:

```
# On CoreLab server and any client machines
<CORELAB_IP>  ledgerloop.lab-core.local
<CORELAB_IP>  ledgerloop-api.lab-core.local
```

Or configure in your router/Pi-hole if using local DNS.

### 8. Create Health Check Endpoint Verification

Create `scripts/health-check.sh`:

```bash
#!/bin/bash

echo "🏥 LedgerLoop Health Check"
echo "=========================="

# Backend health
echo -n "Backend API: "
if curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Frontend
echo -n "Frontend:    "
if curl -sf http://localhost:3000 > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Database (via API)
echo -n "Database:    "
HEALTH=$(curl -sf http://localhost:8000/api/health/detailed 2>/dev/null)
if echo "$HEALTH" | grep -q '"database":"ok"'; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Docker containers
echo ""
echo "Container Status:"
docker ps --filter name=ledgerloop --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Output Required

Create these files:
1. `docker-compose.corelab.yml`
2. `.env.corelab`
3. `scripts/deploy-corelab.sh`
4. `scripts/backup-data.sh`
5. `scripts/restore-data.sh`
6. `scripts/health-check.sh`

Create `CORELAB_DEPLOY.md` with:
- Step-by-step deployment instructions
- DNS/networking setup
- Backup/restore procedures
- Troubleshooting guide

## Rules
- All scripts must be executable (`chmod +x`)
- All configs must work on Linux (CoreLab is Linux)
- Data persistence is CRITICAL - DuckDB file must survive container restarts
- Use Traefik labels if Traefik is available, otherwise direct port mapping
