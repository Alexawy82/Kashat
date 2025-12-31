# Deploy Kashat to CoreLab - Claude Code Prompt

## Context
Deploy Kashat personal finance app to CoreLab home server.

**Server:** Ubuntu mini PC with Docker, Portainer, Traefik (already running)
**Repo:** https://github.com/Alexawy82/Floss
**Stack:** Next.js 14 frontend + FastAPI backend + SQLite + LM Studio AI

**The project already has:**
- `scripts/deploy-corelab.sh` - Deploy script (needs docker-compose.corelab.yml)
- `.env.example` - Environment template
- `requirements.txt` - Python dependencies (root level)
- `apps/web/next.config.js` - Already has `output: 'standalone'`

---

## TASK: Create Missing Docker Files

### 1. Create `docker-compose.corelab.yml` (project root)

```yaml
version: '3.8'

services:
  # ===================
  # BACKEND (FastAPI)
  # ===================
  kashat-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: kashat-backend
    restart: unless-stopped
    environment:
      - KASHAT_DATA_DIR=/data
      - KASHAT_ENV=production
      - KASHAT_JWT_SECRET=${KASHAT_JWT_SECRET}
      - KASHAT_AI_PROVIDER=${KASHAT_AI_PROVIDER:-lmstudio}
      - KASHAT_AI_LMSTUDIO_BASE_URL=${KASHAT_AI_LMSTUDIO_BASE_URL:-http://host.docker.internal:1234/v1}
      - KASHAT_CORS=http://kashat.lab-core.local,http://lab-core.local:3000,http://localhost:3000
      - PYTHONUNBUFFERED=1
    volumes:
      - /opt/kashat/data:/data
    networks:
      - traefik-net
      - kashat-internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kashat-api.rule=Host(`kashat.lab-core.local`) && PathPrefix(`/api`)"
      - "traefik.http.routers.kashat-api.entrypoints=web"
      - "traefik.http.services.kashat-api.loadbalancer.server.port=8000"
      - "traefik.docker.network=traefik-net"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    extra_hosts:
      - "host.docker.internal:host-gateway"

  # ===================
  # FRONTEND (Next.js)
  # ===================
  kashat-frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: kashat-frontend
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_BASE=/api
      - LEDGERLOOP_BACKEND_ORIGIN=http://kashat-backend:8000
      - NEXT_PUBLIC_ENABLE_REALTIME=0
    depends_on:
      kashat-backend:
        condition: service_healthy
    networks:
      - traefik-net
      - kashat-internal
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kashat-web.rule=Host(`kashat.lab-core.local`)"
      - "traefik.http.routers.kashat-web.entrypoints=web"
      - "traefik.http.services.kashat-web.loadbalancer.server.port=3000"
      - "traefik.docker.network=traefik-net"
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

networks:
  traefik-net:
    external: true
  kashat-internal:
    driver: bridge
```

### 2. Create `Dockerfile.backend` (project root)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY apps/backend/src ./src

# Create data directory
RUN mkdir -p /data

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "kashat.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 3. Create `Dockerfile.frontend` (project root)

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY apps/web/package.json apps/web/pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile || pnpm install

# Copy source code
COPY apps/web/ .

# Build arguments for environment
ARG NEXT_PUBLIC_API_BASE=/api
ARG NEXT_PUBLIC_ENABLE_REALTIME=0
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_ENABLE_REALTIME=$NEXT_PUBLIC_ENABLE_REALTIME
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build the application
RUN pnpm build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application from standalone output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### 4. Create `.env.corelab` (project root)

```env
# Kashat CoreLab Environment Configuration
# Copy to .env and update KASHAT_JWT_SECRET before deploying

# =============================================================================
# REQUIRED - Security
# =============================================================================
# Generate with: openssl rand -hex 32
KASHAT_JWT_SECRET=CHANGE_ME_GENERATE_WITH_OPENSSL

# =============================================================================
# Data Storage
# =============================================================================
KASHAT_DATA_DIR=/opt/kashat/data

# =============================================================================
# Environment
# =============================================================================
KASHAT_ENV=production
KASHAT_LOG_LEVEL=INFO

# =============================================================================
# AI Configuration (LM Studio on local network)
# =============================================================================
# Update IP to your LM Studio machine
KASHAT_AI_PROVIDER=lmstudio
KASHAT_AI_LMSTUDIO_BASE_URL=http://192.168.1.XXX:1234/v1

# Optional: OpenAI fallback
# OPENAI_API_KEY=sk-...

# =============================================================================
# CORS (adjust domains as needed)
# =============================================================================
KASHAT_CORS=http://kashat.lab-core.local,http://lab-core.local:3000

# =============================================================================
# Frontend
# =============================================================================
NEXT_PUBLIC_API_BASE=/api
NEXT_PUBLIC_ENABLE_REALTIME=0
```

### 5. Add Health Check Endpoint (if not exists)

Check if `apps/backend/src/kashat/api/main.py` has a health endpoint. If not, add:

```python
@app.get("/api/health")
def health_check():
    """Health check endpoint for Docker/Traefik."""
    return {"status": "healthy", "service": "kashat-api"}
```

### 6. Update `scripts/health-check.sh`

```bash
#!/bin/bash
# Health check script for Kashat deployment

echo "Checking backend health..."
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "000")
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo "✅ Backend: healthy"
else
    echo "❌ Backend: unhealthy (HTTP $BACKEND_HEALTH)"
fi

echo "Checking frontend health..."
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
if [ "$FRONTEND_HEALTH" = "200" ]; then
    echo "✅ Frontend: healthy"
else
    echo "❌ Frontend: unhealthy (HTTP $FRONTEND_HEALTH)"
fi

if [ "$BACKEND_HEALTH" = "200" ] && [ "$FRONTEND_HEALTH" = "200" ]; then
    echo ""
    echo "🎉 All services healthy!"
    exit 0
else
    echo ""
    echo "⚠️  Some services are not healthy"
    exit 1
fi
```

---

## Deployment Steps

### On CoreLab Server:

```bash
# 1. Clone repo (or pull if exists)
cd /opt/stacks
git clone https://github.com/Alexawy82/Floss.git kashat 2>/dev/null || (cd kashat && git pull)
cd kashat

# 2. Create .env from template
cp .env.corelab .env

# 3. Generate and set JWT secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/CHANGE_ME_GENERATE_WITH_OPENSSL/$JWT_SECRET/" .env

# 4. Update LM Studio IP in .env (if using AI features)
# Edit .env and set KASHAT_AI_LMSTUDIO_BASE_URL to your LM Studio machine IP

# 5. Create data directories
sudo mkdir -p /opt/kashat/data
sudo mkdir -p /opt/kashat/backups
sudo chown -R 1000:1000 /opt/kashat

# 6. Ensure traefik network exists
docker network create traefik-net 2>/dev/null || true

# 7. Build and deploy
docker compose -f docker-compose.corelab.yml build
docker compose -f docker-compose.corelab.yml up -d

# 8. Check logs
docker compose -f docker-compose.corelab.yml logs -f

# 9. Verify
./scripts/health-check.sh
```

### Or use the deploy script:
```bash
chmod +x scripts/deploy-corelab.sh
./scripts/deploy-corelab.sh
```

---

## DNS Configuration

Add to your local DNS or router:
```
kashat.lab-core.local → CoreLab IP (e.g., 192.168.1.100)
```

Or add to `/etc/hosts` on client machines:
```
192.168.1.100  kashat.lab-core.local
```

---

## Migrate Existing Data

If you have data from Windows development:

```bash
# Copy SQLite database from Windows
# Source: C:\Users\Marwan\Desktop\AI\Flos\data\ledgerloop.sqlite
# Destination: /opt/kashat/data/

scp user@windows-pc:/path/to/ledgerloop.sqlite /opt/kashat/data/

# Fix permissions
sudo chown 1000:1000 /opt/kashat/data/ledgerloop.sqlite
```

---

## Verification Checklist

After deployment:
- [ ] `curl http://kashat.lab-core.local/api/health` returns `{"status": "healthy"}`
- [ ] `http://kashat.lab-core.local` loads the dashboard
- [ ] Transactions page shows data
- [ ] AI categorization works (if LM Studio configured)

---

## Troubleshooting

```bash
# View logs
docker compose -f docker-compose.corelab.yml logs -f kashat-backend
docker compose -f docker-compose.corelab.yml logs -f kashat-frontend

# Restart services
docker compose -f docker-compose.corelab.yml restart

# Rebuild from scratch
docker compose -f docker-compose.corelab.yml down
docker compose -f docker-compose.corelab.yml build --no-cache
docker compose -f docker-compose.corelab.yml up -d

# Check Traefik dashboard for routing
# Usually at http://lab-core.local:8080/dashboard/

# Enter container for debugging
docker exec -it kashat-backend bash
docker exec -it kashat-frontend sh
```
