# Kashat Deployment Guide

This guide covers deploying Kashat in various environments, from local development to production servers.

---

## Table of Contents

- [Deployment Options Overview](#deployment-options-overview)
- [Local Development](#local-development)
- [Docker Compose (Recommended)](#docker-compose-recommended)
- [Manual Installation](#manual-installation)
- [Production Deployment](#production-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [Home Server / Raspberry Pi](#home-server--raspberry-pi)
- [Cloud Deployment](#cloud-deployment)
- [Environment Configuration](#environment-configuration)
- [Security Hardening](#security-hardening)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Deployment Options Overview

| Method | Best For | Complexity | Features |
|--------|----------|------------|----------|
| **Docker Compose** | Most users | Low | Full features, easy updates |
| **Manual** | Developers | Medium | Full control, debugging |
| **Production Docker** | VPS/Cloud | Medium | SSL, monitoring, backups |
| **Home Server** | Self-hosters | Low-Medium | Always-on, private |

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Backend Setup

```bash
# Clone repository
git clone https://github.com/Alexawy82/Floss.git kashat
cd kashat

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment
export PYTHONPATH=apps/backend/src
cp .env.example .env
# Edit .env and set KASHAT_JWT_SECRET

# Run backend
uvicorn kashat.api.main:app --reload --port 8000
```

### Frontend Setup

```bash
# In a new terminal
cd kashat/apps/web

# Install dependencies
npm install

# Create environment file
cat > .env.local << EOF
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
NEXT_PUBLIC_ENABLE_REALTIME=0
EOF

# Run frontend
npm run dev
```

### Development URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Docker Compose (Recommended)

### Basic Deployment

```bash
# Clone and configure
git clone https://github.com/Alexawy82/Floss.git kashat
cd kashat
cp .env.example .env

# Generate secure JWT secret
echo "KASHAT_JWT_SECRET=$(openssl rand -hex 32)" >> .env

# Start services
docker compose up -d

# Verify
docker compose ps
curl http://localhost:8000/api/health
```

### Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
services:
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
      - KASHAT_CORS=${KASHAT_CORS:-http://localhost:3000}
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - kashat-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    extra_hosts:
      - "host.docker.internal:host-gateway"

  kashat-frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
      args:
        - NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE:-/api}
        - LEDGERLOOP_BACKEND_ORIGIN=http://kashat-backend:8000
    container_name: kashat-frontend
    restart: unless-stopped
    environment:
      - NODE_ENV=production
    ports:
      - "${WEB_PORT:-3000}:3000"
    depends_on:
      kashat-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000', (r) => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  kashat-data:
```

### Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## Manual Installation

### Backend Installation

```bash
# System dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Create application directory
sudo mkdir -p /opt/kashat
sudo chown $USER:$USER /opt/kashat

# Clone and setup
cd /opt/kashat
git clone https://github.com/Alexawy82/Floss.git .
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Create data directory
mkdir -p ~/.kashat

# Test run
PYTHONPATH=apps/backend/src uvicorn kashat.api.main:app --host 0.0.0.0 --port 8000
```

### Frontend Installation

```bash
# Install Node.js 20 (using NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Build frontend
cd /opt/kashat/apps/web
npm ci
npm run build

# Create environment
cat > .env.production << EOF
NEXT_PUBLIC_API_BASE=http://your-server:8000/api
EOF

# Start
npm start
```

### Systemd Service (Backend)

Create `/etc/systemd/system/kashat-backend.service`:

```ini
[Unit]
Description=Kashat Backend API
After=network.target

[Service]
Type=simple
User=kashat
Group=kashat
WorkingDirectory=/opt/kashat
Environment="PYTHONPATH=/opt/kashat/apps/backend/src"
EnvironmentFile=/opt/kashat/.env
ExecStart=/opt/kashat/venv/bin/uvicorn kashat.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable kashat-backend
sudo systemctl start kashat-backend
sudo systemctl status kashat-backend
```

### Systemd Service (Frontend)

Create `/etc/systemd/system/kashat-frontend.service`:

```ini
[Unit]
Description=Kashat Frontend
After=network.target kashat-backend.service

[Service]
Type=simple
User=kashat
Group=kashat
WorkingDirectory=/opt/kashat/apps/web
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Production Deployment

### Pre-Production Checklist

- [ ] Strong JWT secret (32+ characters)
- [ ] HTTPS/TLS configured
- [ ] Firewall configured
- [ ] Rate limiting enabled
- [ ] Backup strategy in place
- [ ] Monitoring configured
- [ ] Log rotation set up

### Production Environment Variables

```bash
# Security (REQUIRED)
KASHAT_JWT_SECRET=<generate with: openssl rand -hex 32>
KASHAT_ENV=production

# CORS (restrict to your domain)
KASHAT_CORS=https://kashat.yourdomain.com

# AI Configuration
KASHAT_AI_PROVIDER=lmstudio
KASHAT_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Rate Limiting
KASHAT_RATE_LIMIT=100/minute

# Logging
KASHAT_LOG_LEVEL=WARNING
```

---

## Reverse Proxy Setup

### Nginx

Create `/etc/nginx/sites-available/kashat`:

```nginx
upstream kashat_backend {
    server 127.0.0.1:8000;
}

upstream kashat_frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name kashat.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name kashat.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/kashat.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/kashat.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # API backend
    location /api {
        proxy_pass http://kashat_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Frontend
    location / {
        proxy_pass http://kashat_frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static file caching
    location /_next/static {
        proxy_pass http://kashat_frontend;
        proxy_cache_valid 60m;
        add_header Cache-Control "public, immutable, max-age=31536000";
    }
}
```

```bash
# Enable and test
sudo ln -s /etc/nginx/sites-available/kashat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Traefik

For Docker deployments with Traefik, use `docker-compose.corelab.yml`:

```yaml
services:
  kashat-backend:
    # ... (same as above)
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kashat-api.rule=Host(`kashat.yourdomain.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.kashat-api.tls=true"
      - "traefik.http.routers.kashat-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.kashat-api.loadbalancer.server.port=8000"

  kashat-frontend:
    # ... (same as above)
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kashat-web.rule=Host(`kashat.yourdomain.com`)"
      - "traefik.http.routers.kashat-web.tls=true"
      - "traefik.http.routers.kashat-web.tls.certresolver=letsencrypt"
      - "traefik.http.services.kashat-web.loadbalancer.server.port=3000"

networks:
  default:
    external: true
    name: traefik-network
```

### Caddy

Create `Caddyfile`:

```
kashat.yourdomain.com {
    # API backend
    handle /api/* {
        reverse_proxy localhost:8000
    }

    # Frontend
    handle {
        reverse_proxy localhost:3000
    }

    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

---

## Home Server / Raspberry Pi

### Raspberry Pi 4 Deployment

Kashat runs well on Raspberry Pi 4 (4GB+ RAM recommended).

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Clone and deploy
git clone https://github.com/Alexawy82/Floss.git kashat
cd kashat
cp .env.example .env
echo "KASHAT_JWT_SECRET=$(openssl rand -hex 32)" >> .env

# Build (this takes longer on Pi)
docker compose build

# Start
docker compose up -d
```

### Performance Tuning for Pi

Edit `.env`:

```bash
# Reduce workers for limited RAM
# In Dockerfile.backend, change --workers 2 to --workers 1

# Disable real-time features to reduce CPU
KASHAT_DISABLE_REALTIME=true
NEXT_PUBLIC_ENABLE_REALTIME=0
```

### Auto-start on Boot

Docker services automatically restart with `restart: unless-stopped`.

---

## Cloud Deployment

### DigitalOcean Droplet

1. Create a Droplet (2GB RAM minimum)
2. SSH into the droplet
3. Follow Docker Compose deployment
4. Configure firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### AWS EC2

1. Launch t3.small instance (2GB RAM)
2. Configure Security Group:
   - SSH (22) from your IP
   - HTTP (80) from anywhere
   - HTTPS (443) from anywhere
3. Follow Docker Compose deployment

### Hetzner Cloud

1. Create CX21 server (2 vCPU, 4GB RAM)
2. Follow Docker Compose deployment
3. Configure firewall in Hetzner console

---

## Environment Configuration

### Complete Environment Reference

```bash
# =============================================================================
# CORE SETTINGS
# =============================================================================
KASHAT_DATA_DIR=/data                    # Data storage location
KASHAT_ENV=production                    # Environment: development|staging|production
KASHAT_LOG_LEVEL=INFO                    # DEBUG|INFO|WARNING|ERROR

# =============================================================================
# SECURITY (REQUIRED)
# =============================================================================
KASHAT_JWT_SECRET=<min-32-chars>         # JWT signing key
KASHAT_ADMIN_TOKEN=<optional>            # Admin API access
KASHAT_CORS=https://app.example.com      # Allowed origins
KASHAT_ALLOW_REGISTRATION=false          # Public registration

# =============================================================================
# AI CONFIGURATION
# =============================================================================
KASHAT_AI_PROVIDER=lmstudio              # lmstudio|ollama|openai
KASHAT_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=                          # For OpenAI provider
KASHAT_AI_MODEL_CATEGORIZE=qwen/qwen3-4b

# =============================================================================
# PERFORMANCE
# =============================================================================
KASHAT_RATE_LIMIT=100/minute             # API rate limiting
KASHAT_DISABLE_REALTIME=false            # Disable WebSocket features

# =============================================================================
# DOCKER PORTS
# =============================================================================
BACKEND_PORT=8000
WEB_PORT=3000

# =============================================================================
# FRONTEND
# =============================================================================
NEXT_PUBLIC_API_BASE=/api
NEXT_PUBLIC_ENABLE_REALTIME=0
```

---

## Security Hardening

### Essential Security Steps

1. **Generate Strong JWT Secret**
   ```bash
   openssl rand -hex 32
   ```

2. **Restrict CORS**
   ```bash
   KASHAT_CORS=https://kashat.yourdomain.com
   ```

3. **Enable Rate Limiting**
   ```bash
   KASHAT_RATE_LIMIT=100/minute
   ```

4. **Use HTTPS**
   - Configure reverse proxy with SSL
   - Use Let's Encrypt for free certificates

5. **Firewall Configuration**
   ```bash
   # Only expose necessary ports
   sudo ufw default deny incoming
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

6. **Regular Updates**
   ```bash
   # Update containers regularly
   docker compose pull
   docker compose up -d
   ```

---

## Backup and Recovery

### Automated Backups

Create `/opt/kashat/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/opt/kashat/backups
DATE=$(date +%Y%m%d_%H%M%S)
DATA_DIR=/opt/kashat/data

# Create backup directory
mkdir -p $BACKUP_DIR

# Stop services briefly for consistent backup
docker compose -f /opt/kashat/docker-compose.yml stop kashat-backend

# Backup database
cp $DATA_DIR/ledgerloop.sqlite $BACKUP_DIR/kashat_$DATE.sqlite

# Restart services
docker compose -f /opt/kashat/docker-compose.yml start kashat-backend

# Compress
gzip $BACKUP_DIR/kashat_$DATE.sqlite

# Keep only last 30 backups
ls -t $BACKUP_DIR/kashat_*.sqlite.gz | tail -n +31 | xargs -r rm

echo "Backup completed: kashat_$DATE.sqlite.gz"
```

```bash
# Make executable and schedule
chmod +x /opt/kashat/backup.sh

# Add to crontab (daily at 3 AM)
echo "0 3 * * * /opt/kashat/backup.sh" | crontab -
```

### Recovery

```bash
# Stop services
docker compose down

# Restore backup
gunzip -k /opt/kashat/backups/kashat_YYYYMMDD.sqlite.gz
cp /opt/kashat/backups/kashat_YYYYMMDD.sqlite /opt/kashat/data/ledgerloop.sqlite

# Restart
docker compose up -d
```

---

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Full health check
curl http://localhost:8000/api/health/full
```

### Prometheus Metrics (Optional)

Enable in `.env`:

```bash
KASHAT_EXPOSE_METRICS=true
```

Access metrics at: `http://localhost:8000/metrics`

### Log Monitoring

```bash
# Docker logs
docker compose logs -f

# Backend logs only
docker compose logs -f kashat-backend

# Last 100 lines
docker compose logs --tail 100
```

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose logs kashat-backend

# Common causes:
# - Invalid JWT_SECRET (must be 32+ chars)
# - Port already in use
# - Permission issues with data directory
```

#### Database Locked

```bash
# Stop all services
docker compose down

# Check for stale lock files
ls -la /opt/kashat/data/*.sqlite*

# Remove lock files (safe if services stopped)
rm /opt/kashat/data/*.sqlite-shm /opt/kashat/data/*.sqlite-wal

# Restart
docker compose up -d
```

#### AI Not Working

```bash
# Check AI provider settings
grep KASHAT_AI .env

# Test LM Studio connectivity
curl http://localhost:1234/v1/models

# Check backend logs for AI errors
docker compose logs kashat-backend | grep -i ai
```

#### Frontend Can't Connect to Backend

```bash
# Check CORS settings
grep KASHAT_CORS .env

# Verify backend is running
curl http://localhost:8000/api/health

# Check frontend environment
docker compose exec kashat-frontend env | grep API
```

#### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce workers in Dockerfile.backend
# Change: --workers 2 to --workers 1

# Rebuild
docker compose build kashat-backend
docker compose up -d
```

---

## Support

- **Documentation:** [docs/](.)
- **Issues:** [GitHub Issues](https://github.com/Alexawy82/Floss/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Alexawy82/Floss/discussions)

---

[Back to README](../README.md) | [Quick Start](QUICKSTART.md)
