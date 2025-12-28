# LedgerLoop Deployment Guide

This guide covers deploying LedgerLoop in various environments.

## Table of Contents

1. [Quick Start (Development)](#quick-start-development)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Security Hardening](#security-hardening)
6. [Monitoring](#monitoring)
7. [Maintenance](#maintenance)

---

## Quick Start (Development)

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### One-Command Setup

```bash
git clone <repository-url>
cd Flos
./setup    # Creates venv, installs dependencies
./start    # Starts backend and frontend
```

### Manual Setup

**Backend:**
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export PYTHONPATH=apps/backend/src
uvicorn ledgerloop.api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd apps/web
npm install
npm run dev
```

Access the application at `http://localhost:3000`

---

## Production Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Create production environment file
cp .env.example .env

# Recommended: bind ports to localhost (single-user mode; auth disabled)
echo "LL_BIND_IP=127.0.0.1" >> .env

# Build and start
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

### Option 2: Bare Metal

**Backend (with Gunicorn):**
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn ledgerloop.api.main:app \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile /var/log/ledgerloop/access.log \
    --error-logfile /var/log/ledgerloop/error.log
```

**Frontend (Static Export):**
```bash
cd apps/web
npm run build
# Serve .next/standalone with Node.js
mkdir -p .next/standalone/.next
cp -R .next/static .next/standalone/.next/static
if [ -d public ]; then cp -R public .next/standalone/public; fi
node .next/standalone/server.js
```

### Option 3: Systemd Services

Create `/etc/systemd/system/ledgerloop-backend.service`:
```ini
[Unit]
Description=LedgerLoop Backend API
After=network.target

[Service]
Type=simple
User=ledgerloop
Group=ledgerloop
WorkingDirectory=/opt/ledgerloop
Environment=PYTHONPATH=/opt/ledgerloop/apps/backend/src
Environment=LEDGERLOOP_DATA_DIR=/var/lib/ledgerloop
Environment=LEDGERLOOP_ENV=production
EnvironmentFile=/etc/ledgerloop/environment
ExecStart=/opt/ledgerloop/.venv/bin/gunicorn ledgerloop.api.main:app \
    --bind 127.0.0.1:8000 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ledgerloop-backend
sudo systemctl start ledgerloop-backend
```

---

## Docker Deployment

### Building Images

```bash
# Build backend
docker build -f Dockerfile.backend -t ledgerloop-backend:latest .

# Build frontend
docker build -f Dockerfile.web -t ledgerloop-web:latest .
```

### Docker Compose Configuration

The included `docker-compose.yml` provides:
- Multi-container setup (backend + frontend)
- Health checks
- Resource limits
- Named volumes for data persistence
- Internal networking

**Key settings:**
```yaml
services:
  backend:
    environment:
      - LEDGERLOOP_CORS=http://localhost:3000
    volumes:
      - ledgerloop-data:/data
    ports:
      - "${LL_BIND_IP:-127.0.0.1}:${BACKEND_PORT:-8000}:8000"

  web:
    environment:
      - NEXT_PUBLIC_API_BASE=/api
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "${LL_BIND_IP:-127.0.0.1}:${WEB_PORT:-3000}:3000"
```

The web server proxies `/api/*` to the backend using a Next.js rewrite. In Docker builds, set the server-side proxy origin via `LEDGERLOOP_BACKEND_ORIGIN` (the provided `docker-compose.yml` does this as a build arg).

### Custom Ports

Override ports via environment:
```bash
BACKEND_PORT=8080 WEB_PORT=3001 docker compose up -d
```

### Data Persistence

Data is stored in a Docker volume:
```bash
# List volumes
docker volume ls

# Backup
docker run --rm -v ledgerloop-data:/data -v $(pwd):/backup alpine \
    tar czf /backup/ledgerloop-backup.tar.gz /data

# Restore
docker run --rm -v ledgerloop-data:/data -v $(pwd):/backup alpine \
    tar xzf /backup/ledgerloop-backup.tar.gz -C /
```

---

## Environment Configuration

### Recommended Variables (Production)

| Variable | Description | Example |
|----------|-------------|---------|
| `LL_BIND_IP` | Host bind IP for Docker ports | `127.0.0.1` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_MAX_UPLOAD_MB` | `50` | Max upload size per file (`0` disables limit) |
| `LEDGERLOOP_DATA_DIR` | `~/.ledgerloop` | Data directory |
| `LEDGERLOOP_ENV` | `development` | Environment mode |
| `LEDGERLOOP_LOG_LEVEL` | `INFO` | Logging level |
| `LEDGERLOOP_CORS` | `*` | Allowed CORS origins |
| `LEDGERLOOP_RATE_LIMIT` | `100/minute` | Default rate limit |

### AI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_AI_PROVIDER` | `lmstudio` | AI provider |
| `LEDGERLOOP_AI_LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | LMStudio URL |
| `OPENAI_API_KEY` | - | OpenAI API key |

### Frontend Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `/api` | Backend API URL |
| `NEXT_PUBLIC_ENABLE_REALTIME` | `0` | Enable WebSocket features |

### Sample Production .env

```bash
# Network (recommended)
LL_BIND_IP=127.0.0.1

# Environment
LEDGERLOOP_ENV=production
LEDGERLOOP_LOG_LEVEL=INFO

# CORS (restrict to your domain)
LEDGERLOOP_CORS=https://app.yourdomain.com

# Data
LEDGERLOOP_DATA_DIR=/var/lib/ledgerloop

# Upload limits
LEDGERLOOP_MAX_UPLOAD_MB=50

# AI (optional)
LEDGERLOOP_AI_PROVIDER=lmstudio
LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

---

## Security Hardening

### 1. Restrict Network Exposure

```bash
# Docker: bind to localhost
LL_BIND_IP=127.0.0.1 docker compose up -d
```

### 2. Restrict CORS (Only If Using Cross-Origin Requests)

```bash
# Production - only allow your domain
LEDGERLOOP_CORS=https://app.yourdomain.com

# Multiple origins
LEDGERLOOP_CORS=https://app.yourdomain.com,https://admin.yourdomain.com
```

### 3. Enable HTTPS

Use a reverse proxy (nginx, Caddy, Traefik) with TLS:

**Nginx Example:**
```nginx
server {
    listen 443 ssl http2;
    server_name app.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Rate Limiting

Rate limiting is enabled by default:
- Login: 5 requests/minute
- API: 100 requests/minute
- Import: 10 requests/minute

### 5. Change Default Credentials

After first login:
1. Go to Settings > Security
2. Change the default password
3. Consider creating a non-admin user for daily use

---

## Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/api/health

# Detailed health
curl http://localhost:8000/api/health/detailed

# Kubernetes probes
curl http://localhost:8000/api/health/live    # Liveness
curl http://localhost:8000/api/health/ready   # Readiness
```

### Prometheus Metrics

Metrics are exposed at `/metrics`:
```bash
curl http://localhost:8000/metrics
```

Available metrics:
- `http_requests_total` - Request count by endpoint
- `http_request_duration_seconds` - Request latency
- `transactions_total` - Total transactions
- `categorized_transactions` - Categorized count
- `ai_categorizations_total` - AI operations

### Usage Statistics

```bash
curl http://localhost:8000/api/ops/usage
```

Returns per-route request counts and p95 latency.

---

## Maintenance

### Database Backup

```bash
# Stop the service first for consistent backup
docker compose stop backend

# Backup
cp /var/lib/ledgerloop/ledgerloop.duckdb /backup/ledgerloop_$(date +%Y%m%d).duckdb

# Restart
docker compose start backend
```

### Log Management

Logs are written to stdout in Docker. For bare metal:
```bash
# Backend logs
tail -f /var/log/ledgerloop/access.log
tail -f /var/log/ledgerloop/error.log

# Rotate logs with logrotate
cat > /etc/logrotate.d/ledgerloop << EOF
/var/log/ledgerloop/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}
EOF
```

### Updates

```bash
# Pull latest code
git pull

# Rebuild images
docker compose build

# Restart with new images
docker compose up -d

# Check migration applied
curl http://localhost:8000/api/health/detailed
```

### Database Migrations

Migrations run automatically on startup. Check status:
```bash
curl http://localhost:8000/api/health/detailed | jq '.database.schema_version'
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

---

*LedgerLoop Deployment Guide - v2.0*
