# Configuration Documentation

## Overview

LedgerLoop uses environment variables for configuration with sensible defaults for local development. Production deployments should override security-critical settings.

---

## Environment Variables

### Security (CRITICAL for Production)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LEDGERLOOP_JWT_SECRET` | "ledgerloop-dev-secret-change-in-production" | **YES** | JWT signing key (min 32 chars) |
| `LEDGERLOOP_ADMIN_TOKEN` | None | No | Admin API token |
| `LEDGERLOOP_CORS` | "*" | No | CORS allowed origins |
| `LEDGERLOOP_ALLOW_REGISTRATION` | false | No | Public user registration |

### Data Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_DATA_DIR` | ~/.ledgerloop | Database and temp file directory |
| `LEDGERLOOP_ENV` | development | Environment (development/staging/production) |
| `LEDGERLOOP_LOG_LEVEL` | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |

### AI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_AI_PROVIDER` | auto | Provider: openai, lmstudio, local, auto |
| `OPENAI_API_KEY` | None | OpenAI API key |
| `LEDGERLOOP_AI_OPENAI_BASE_URL` | https://api.openai.com/v1 | OpenAI endpoint |
| `LEDGERLOOP_AI_OPENAI_MODEL` | gpt-4o-mini | OpenAI model |
| `LEDGERLOOP_AI_LMSTUDIO_BASE_URL` | http://localhost:1234/v1 | LM Studio endpoint |
| `LEDGERLOOP_AI_LMSTUDIO_MODEL` | local-model | LM Studio model |
| `LEDGERLOOP_AI_TIMEOUT` | 30 | Request timeout (seconds) |
| `LEDGERLOOP_AI_CONNECT_TIMEOUT` | 5 | Connection timeout (seconds) |
| `LEDGERLOOP_AI_MAX_RETRIES` | 2 | Retry attempts |
| `LEDGERLOOP_AI_MAX_CONCURRENCY` | 2 | Concurrent requests |
| `LEDGERLOOP_AI_BATCH_SIZE` | 5 | Batch size |
| `LEDGERLOOP_AI_CONFIDENCE_THRESHOLD` | 0.7 | Min confidence |
| `LEDGERLOOP_AI_TEMPERATURE` | 0.1 | LLM temperature |
| `LEDGERLOOP_AI_DEBUG` | false | Debug logging |

### Real-time Features

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_DISABLE_REALTIME` | true | Disable WebSocket features |
| `NEXT_PUBLIC_WS_TOKEN` | MaroMaro | WebSocket auth token |
| `NEXT_PUBLIC_ENABLE_REALTIME` | 0 | Enable real-time UI |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_RATE_LIMIT` | 100/minute | Default rate limit |

### Docker Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | 8000 | Backend port |
| `WEB_PORT` | 3000 | Frontend port |
| `LL_BIND_IP` | 127.0.0.1 | Bind IP address |

### Frontend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | /api | API base URL |
| `LEDGERLOOP_BACKEND_ORIGIN` | http://localhost:8000 | Backend origin |

---

## Configuration Files

### requirements.txt

Python dependencies for the backend:

```
fastapi==0.115.0
uvicorn==0.37.0
duckdb==1.1.3
python-dotenv==1.0.1
pdfplumber==0.11.4
python-multipart==0.0.9
pyarrow==16.1.0
requests==2.32.3
openai==1.51.0
numpy==1.26.4
pytest==8.2.1
pytest-cov==5.0.0
pytest-asyncio==0.23.8
httpx==0.27.2
prometheus-client==0.20.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
slowapi==0.1.9
gunicorn==22.0.0
```

### package.json (Frontend)

```json
{
  "name": "ledgerloop-web",
  "version": "0.1.0",
  "dependencies": {
    "next": "14.2.35",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@tanstack/react-query": "^5.90.12",
    "@tanstack/react-table": "^8.21.3",
    "zustand": "^5.0.0",
    "tailwindcss": "^3.4.17",
    "recharts": "^3.2.1",
    "lucide-react": "^0.544.0"
  }
}
```

---

## Docker Configuration

### docker-compose.yml

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ledgerloop-backend
    restart: unless-stopped
    ports:
      - "${LL_BIND_IP:-127.0.0.1}:${BACKEND_PORT:-8000}:8000"
    volumes:
      - ledgerloop-data:/data
    environment:
      - LEDGERLOOP_JWT_SECRET=${LEDGERLOOP_JWT_SECRET:-ledgerloop-dev-secret-change-in-production}
      - LEDGERLOOP_CORS=${LEDGERLOOP_CORS:-*}
      - LEDGERLOOP_ENV=production
      - LEDGERLOOP_LOG_LEVEL=INFO
      - LEDGERLOOP_DISABLE_REALTIME=true
      - LEDGERLOOP_AI_PROVIDER=lmstudio
      - LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G

  web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: ledgerloop-web
    restart: unless-stopped
    ports:
      - "${LL_BIND_IP:-127.0.0.1}:${WEB_PORT:-3000}:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_BASE=/api
      - NEXT_PUBLIC_ENABLE_REALTIME=0
    depends_on:
      backend:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

volumes:
  ledgerloop-data:
    driver: local

networks:
  default:
    name: ledgerloop-net
```

### Dockerfile.backend

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn websockets bcrypt

# Production stage
FROM python:3.12-slim
RUN useradd -m -s /bin/bash ledgerloop
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY apps/backend/src /app/src

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV LEDGERLOOP_DATA_DIR=/data
ENV LEDGERLOOP_ENV=production

USER ledgerloop
EXPOSE 8000

CMD ["gunicorn", "ledgerloop.api.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker"]
```

### Dockerfile.web

```dockerfile
# Build stage
FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

CMD ["node", "server.js"]
```

---

## Testing Configuration

### pytest.ini

```ini
[pytest]
testpaths = apps/backend/tests
pythonpath = apps/backend/src
addopts = -q --cov=ledgerloop.api --cov=ledgerloop.db --cov=ledgerloop.transfers --cov=ledgerloop.recurring --cov-report=term-missing --cov-fail-under=45
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning:passlib
    ignore::DeprecationWarning:jose.jwt
```

### .coveragerc

```ini
[run]
omit =
    */ledgerloop/ai_*.py
    */ledgerloop/analytics/*.py
    */ledgerloop/ingest_pdf.py
    */ledgerloop/parse/*.py
    */ledgerloop/cli.py

[report]
exclude_lines =
    pragma: no cover
    if TYPE_CHECKING:
    @overload
```

### playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: { timeout: 10000 },
  use: {
    baseURL: process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

---

## Frontend Configuration

### next.config.js

```javascript
module.exports = {
  output: 'standalone',
  distDir: process.env.NODE_ENV === 'production' ? '.next' : '/tmp/ll_next',

  env: {
    NEXT_PUBLIC_WS_TOKEN: process.env.NEXT_PUBLIC_WS_TOKEN || 'MaroMaro',
    NEXT_PUBLIC_ENABLE_REALTIME: process.env.NEXT_PUBLIC_ENABLE_REALTIME || '0',
  },

  async rewrites() {
    const backendOrigin = process.env.LEDGERLOOP_BACKEND_ORIGIN ||
      (process.env.NEXT_PUBLIC_API_BASE?.startsWith('http')
        ? new URL(process.env.NEXT_PUBLIC_API_BASE).origin
        : 'http://localhost:8000');
    return [
      { source: '/api/:path*', destination: `${backendOrigin}/api/:path*` },
    ];
  },

  async redirects() {
    return [
      { source: '/analyze', destination: '/ai', permanent: true },
      { source: '/analytics', destination: '/', permanent: true },
      { source: '/categories', destination: '/settings/categories', permanent: true },
      { source: '/rules', destination: '/settings/automation', permanent: true },
      { source: '/pulse', destination: '/settings/system', permanent: true },
    ];
  },
};
```

### tailwind.config.js

```javascript
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        // ... more colors
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts", "/tmp/ll_next/types/**/*.ts"],
  "exclude": ["node_modules", "e2e", "**/*.test.ts", "**/*.spec.ts", "archive"]
}
```

---

## Makefile

```makefile
.PHONY: dev-backend run-backend test smoke dev dev-down dev-logs dev-health determinism-check

export PYTHONPATH := apps/backend/src

dev-backend:
	uvicorn ledgerloop.api.main:app --reload --port 8000

run-backend:
	uvicorn ledgerloop.api.main:app --host 0.0.0.0 --port 8000

test:
	pytest -q

smoke:
	python scripts/smoke_test.py

dev:
	./scripts/dev_up.sh

dev-down:
	./scripts/dev_down.sh

dev-logs:
	./scripts/dev_up.sh && docker-compose logs -f

dev-health:
	./scripts/dev_up.sh && ./scripts/health-check.sh

determinism-check:
	python scripts/determinism_check.py
```

---

## Runtime Settings

Settings can be configured at runtime via the `/api/settings` endpoint:

| Setting | Type | Description |
|---------|------|-------------|
| recurring_tolerance | float | Recurring detection tolerance |
| tx_default_sort_by | string | Default transaction sort field |
| tx_default_sort_dir | string | Default sort direction |
| tx_include_transfers_default | bool | Include transfers by default |
| ai_provider | string | AI provider selection |
| ai_auto_categorize_on_import | bool | Auto-categorize on import |
| ai_auto_categorize_min_conf | float | Min confidence for auto-apply |
| ai_auto_create_rules | bool | Auto-create rules from patterns |
| dashboard_default_period | string | Dashboard default period |
| dashboard_show_ai | bool | Show AI features on dashboard |
| realtime_enabled | bool | Enable real-time updates |
| sqlite_wal_mode | bool | Use WAL mode |

---

*Generated by Claude Code Audit - December 27, 2025*
