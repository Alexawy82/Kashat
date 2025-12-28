# LedgerLoop Production Status

**Status:** PRODUCTION READY
**Last Updated:** December 20, 2025
**Version:** 1.0.0

---

## System Overview

LedgerLoop is a local-first personal finance application with AI-powered transaction analysis. All data stays on your machine - no cloud services required.

### Architecture
- **Backend:** FastAPI + DuckDB (Python 3.11+)
- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui
- **AI:** Optional LMStudio integration for local LLM processing

---

## Current Deployment Status

### Backend API: HEALTHY
```
http://127.0.0.1:8000/api/health
{"status":"ok","version":"1.0.0"}
```

### Frontend: RUNNING
```
http://127.0.0.1:3000
All pages returning HTTP 200
```

---

## API Endpoints: 203 Total

### Core Endpoints (All Verified)

| Category | Endpoint | Status |
|----------|----------|--------|
| Health | `/api/health` | OK |
| Transactions | `/api/transactions` | OK |
| Categories | `/api/categories` | OK |
| Rules | `/api/rules` | OK |
| Recurring | `/api/recurring/*` | OK |
| Transfers | `/api/transfers/*` | OK |
| Accounts | `/api/accounts` | OK |
| Settings | `/api/settings` | OK |
| Analytics | `/api/analytics/*` | OK |
| Imports | `/api/imports/*` | OK |
| Export | `/api/export/*` | OK |
| Intelligence | `/api/intelligence/*` | OK |
| AI | `/api/ai/*` | OK |
| Admin | `/api/admin/*` | OK |

### AI/Intelligence Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/api/intelligence/health` | Financial health score |
| `/api/intelligence/behavior` | Spending behavior analysis |
| `/api/intelligence/insights` | Personalized insights |
| `/api/intelligence/feed` | Unified intelligence feed |
| `/api/intelligence/subscriptions` | Subscription detection |
| `/api/ai/categories/*` | AI categorization |
| `/api/ai/merchant-memory/*` | Merchant learning |
| `/api/ai/duplicates/*` | Duplicate detection |
| `/api/analytics/ai/anomalies` | Anomaly detection |

---

## Frontend Pages: 10 Total

| Page | Route | Status |
|------|-------|--------|
| Dashboard | `/` | OK |
| Transactions | `/transactions` | OK |
| Analytics | `/analytics` | OK |
| Categories | `/categories` | OK |
| Import | `/import` | OK |
| Rules | `/rules` | OK |
| Recurring | `/recurring` | OK |
| Transfers | `/transfers` | OK |
| Settings | `/settings` | OK |
| Pulse | `/pulse` | OK |

---

## Recent Fixes Applied

### Build Fixes (December 20, 2025)
- Replaced `@hey-api/client-fetch` with simple fetch wrapper
- Fixed uppercase HTTP methods (`GET` -> `get`)
- Made Transaction type fields optional to match backend
- Removed stale archive/examples folders
- Fixed double `/api/api` URL issue
- Installed missing dependencies (`@tanstack/react-table`, `dropdown-menu`)

### Infrastructure
- DuckDB self-heal on schema errors
- Proper CORS configuration
- Environment variable handling

---

## Quick Start

### Development Mode
```bash
# Terminal 1: Backend
cd /path/to/Flos
source .venv/bin/activate
export PYTHONPATH=apps/backend/src
export LEDGERLOOP_DATA_DIR=./data
export LEDGERLOOP_CORS="*"
uvicorn ledgerloop.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
cd apps/web
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev -- -p 3000
```

### Production Mode
```bash
# Build frontend
cd apps/web
npm run build

# Start with production settings
export LEDGERLOOP_CORS="http://your-domain.com"
export LEDGERLOOP_API_TOKEN="your-secure-token"
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LEDGERLOOP_DATA_DIR` | Yes | Data directory for DuckDB |
| `LEDGERLOOP_CORS` | Yes | CORS origins (use `*` for dev) |
| `NEXT_PUBLIC_API_BASE` | Yes | Backend URL without `/api` |
| `LEDGERLOOP_API_TOKEN` | Prod | API authentication token |
| `LEDGERLOOP_ADMIN_TOKEN` | Prod | Admin endpoint token |
| `LEDGERLOOP_AI_LMSTUDIO_BASE_URL` | No | LMStudio URL for AI |

---

## Health Checks

### Backend
```bash
curl http://127.0.0.1:8000/api/health
```

### Frontend
```bash
curl -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/
```

### All Pages
```bash
for page in "/" "/transactions" "/analytics" "/categories" "/import" "/rules" "/settings"; do
  echo "$page: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000$page)"
done
```

---

## Known Limitations

1. **Single-user mode**: No multi-tenant support
2. **DuckDB single-writer**: One backend process only
3. **AI requires LMStudio**: Local AI features need LMStudio running
4. **Local-first**: No cloud sync (by design)

---

## Test Suite

```bash
# Backend tests
cd /path/to/Flos
source .venv/bin/activate
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests -v

# Frontend type check
cd apps/web
npm run build
```

---

## Monitoring

- **Prometheus metrics:** `GET /metrics`
- **Usage stats:** `GET /api/ops/usage`
- **Backend logs:** `logs/backend.log`
- **Frontend logs:** `/tmp/web.log` (dev mode)

---

*Last verified: December 20, 2025*
