# API Reference

## Overview

The LedgerLoop API provides **150+ endpoints** organized into 21 route modules, all prefixed with `/api`.

---

## Route Modules

| Module | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| health | /api/health | 4 | Health checks |
| transactions | /api/transactions | 8 | Transaction CRUD |
| categories | /api/categories | 6 | Category management |
| rules | /api/rules | 8 | Rule engine |
| accounts | /api/accounts | 2 | Account management |
| settings | /api/settings | 4 | Settings |
| imports | /api/imports | 15 | File import |
| transfers | /api/transfers | 12 | Transfer detection |
| recurring | /api/recurring | 30+ | Recurring detection |
| analytics | /api/analytics | 20+ | Analytics |
| export | /api/export | 4 | Data export |
| audit | /api/audit | 2 | Audit logs |
| detect | /api/detect | 5 | Detection ops |
| p2p | /api/p2p | 15 | P2P detection |
| workflows | /api/workflows | 3 | Workflow CRUD |
| ai | /api/ai | 40+ | AI operations |
| ai_categories | /api/ai-categories | 10 | AI categories |
| ai_enhanced | /api/ai-enhanced | 5 | Enhanced AI |
| ai_workflow | /api/ai-workflow | 10 | AI workflows |
| intelligence | /api/intelligence | 10 | Intelligence |
| admin | /api/admin | 15 | Admin ops |

---

## Core Endpoints

### Health

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/health | Basic health check |
| GET | /api/health/live | Liveness probe |
| GET | /api/health/ready | Readiness probe |
| GET | /api/health/detailed | Component status |

### Transactions

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/transactions | List with filters |
| GET | /api/transactions/{tx_id} | Get single |
| PATCH | /api/transactions/{tx_id} | Update flags |
| DELETE | /api/transactions/{tx_id} | Delete |
| POST | /api/transactions/{tx_id}/category | Assign category |
| GET | /api/transactions/stats | Statistics |
| POST | /api/transactions/batch | Get multiple by IDs |

**Query Parameters (GET /transactions):**
- `account_id` - Filter by account
- `start_date`, `end_date` - Date range
- `category_id` - Filter by category
- `uncategorized` - Only uncategorized
- `include_transfers` - Include transfers
- `is_business`, `is_income` - Flags
- `desc` - Search description
- `sort_by`, `sort_dir` - Sorting
- `limit`, `offset` - Pagination

### Categories

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/categories | List all |
| POST | /api/categories | Create |
| GET | /api/categories/{id}/usage | Usage stats |
| PATCH | /api/categories/{id} | Update |
| DELETE | /api/categories/{id} | Delete |
| POST | /api/categories/merge | Merge categories |

### Rules

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/rules | List all |
| POST | /api/rules | Create |
| PATCH | /api/rules/{id} | Update |
| DELETE | /api/rules/{id} | Delete |
| GET | /api/rules/export | Export JSON |
| POST | /api/rules/import | Import JSON |
| POST | /api/rules/preview | Preview matches |
| POST | /api/rules/{id}/apply | Apply single |
| POST | /api/rules/apply-all | Apply all |

---

## Import Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/imports/csv | Upload CSV |
| POST | /api/imports/pdf | Upload PDF |
| POST | /api/imports/bulk | Bulk upload |
| POST | /api/imports/parse | Create/resume run |
| GET | /api/imports/runs | List runs |
| GET | /api/imports/files | List files |
| GET | /api/imports/periods | List periods |
| GET | /api/imports/runs/{id}/files | Run files |
| GET | /api/imports/runs/{id}/summary | Run summary |
| DELETE | /api/imports/runs/{id} | Delete run |
| POST | /api/imports/runs/{id}/reprocess | Reprocess |
| GET | /api/imports/{id}/ai-analysis | AI analysis |
| POST | /api/imports/suggest-rules | Rule suggestions |
| GET | /api/imports/report/{id} | Download report |

---

## Analytics Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/analytics/monthly | Monthly summary |
| GET | /api/analytics/category-monthly | By category |
| GET | /api/analytics/merchants | Top merchants |
| GET | /api/analytics/cashflow | Cashflow totals |
| GET | /api/analytics/summary | Unified summary |
| GET | /api/analytics/recurring | Recurring summary |
| GET | /api/analytics/dashboard | Full dashboard |
| GET | /api/analytics/predictions | Predictions |
| GET | /api/analytics/ai/spending-patterns | AI patterns |
| GET | /api/analytics/ai/trends | AI trends |
| GET | /api/analytics/ai/anomalies | Anomalies |
| GET | /api/analytics/ai/forecasts/spending | Spending forecast |
| GET | /api/analytics/ai/forecasts/income | Income forecast |
| GET | /api/analytics/ai/forecasts/cashflow | Cashflow forecast |
| POST | /api/analytics/ai/comprehensive-insights | All insights |

---

## Transfer Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/transfers | List transfers |
| POST | /api/transfers/confirm | Confirm pair |
| POST | /api/transfers/reject | Reject pair |
| POST | /api/transfers/suggest_v2 | Basic detection |
| POST | /api/transfers/suggest_v3 | Hybrid detection |
| POST | /api/transfers/ai/detect | AI detection job |
| GET | /api/transfers/ai/job/{id} | Job status |
| POST | /api/transfers/ai/analyze-pair | Analyze pair |
| POST | /api/transfers/ai/feedback | Submit feedback |
| POST | /api/transfers/group/{id}/analytics | Toggle analytics |

---

## Recurring Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/recurring/suggest | Run detection |
| GET | /api/recurring | List series |
| GET | /api/recurring/confirmed | Confirmed only |
| GET | /api/recurring/pending | Pending only |
| POST | /api/recurring/confirm | Confirm series |
| POST | /api/recurring/reject | Reject series |
| GET | /api/recurring/{id}/transactions | Series transactions |
| POST | /api/recurring/reclassify | Force reclassify |
| POST | /api/recurring/merge-duplicates | Merge duplicates |
| GET | /api/recurring/by-type/{type} | Filter by type |
| GET | /api/recurring/summary | Summary by type |
| GET | /api/recurring/insights | NLP insights |
| GET | /api/recurring/insights/cash-flow | Cash flow forecast |
| GET | /api/recurring/insights/upcoming | Upcoming payments |
| GET | /api/recurring/intelligence/cache-stats | Cache stats |
| POST | /api/recurring/intelligence/analyze | Analyze merchant |
| POST | /api/recurring/confirm/{id}/with-learning | Confirm + learn |

---

## P2P Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/p2p/summary | Grouped summary |
| GET | /api/p2p/transactions | Drill down |
| POST | /api/p2p/detect | Run detection |
| GET | /api/p2p/detected | List detected |
| GET | /api/p2p/counterparties | List counterparties |
| GET | /api/p2p/counterparties/{id}/transactions | Counterparty txns |
| POST | /api/p2p/merge-counterparties | Merge |
| POST | /api/p2p/enrich | AI enrich all |
| POST | /api/p2p/enrich/{id} | Enrich single |
| GET | /api/p2p/enrichment-stats | Stats |
| GET | /api/p2p/stats | Overall stats |
| GET | /api/p2p/unlinked-recurring | Unlinked |
| POST | /api/p2p/link-recurring | Link to recurring |

---

## AI Endpoints

### Core AI

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/ai/analyze/transaction/{id} | Analyze single |
| POST | /api/ai/analyze/bulk | Bulk analysis |
| POST | /api/ai/normalize/merchant | Extract merchant |
| GET | /api/ai/stats | AI statistics |
| GET | /api/ai/categorization/status | Job status |
| GET | /api/ai/ping | Test connectivity |
| GET | /api/ai/status | Provider status |
| POST | /api/ai/reset | Reset service |

### Bulk Jobs

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/ai/enhance/uncategorized | Start job |
| GET | /api/ai/bulk-job/{id} | Job status |
| POST | /api/ai/bulk-job/{id}/cancel | Cancel |
| POST | /api/ai/bulk-job/{id}/retry | Retry |
| GET | /api/ai/bulk-jobs | List jobs |

### Queue Management

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/ai/queue/stats | Queue stats |
| POST | /api/ai/queue/pause | Pause |
| POST | /api/ai/queue/resume | Resume |
| POST | /api/ai/queue/settings | Update settings |

### Suggestions

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/ai/suggestions/categories/{id} | Get suggestions |
| GET | /api/ai/suggestions/smart-categories/{id} | Enhanced |
| POST | /api/ai/suggestions/apply-smart-category | Apply |
| POST | /api/ai/suggestions/opt-out | Opt out |

### Duplicates

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/ai/duplicates/detect | Find duplicates |
| POST | /api/ai/duplicates/merge | Merge |
| GET | /api/ai/duplicates/stats | Stats |

### Categories

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/ai/categories/gap-analysis | Gap analysis |
| POST | /api/ai/categories/bootstrap | Create missing |
| POST | /api/ai/categories/bulk-fix | One-click fix |
| GET | /api/ai/categories/success-metrics | Metrics |

### Merchant Memory

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/ai/merchant-memory/learn | Learn |
| POST | /api/ai/merchant-memory/backfill | Backfill |
| GET | /api/ai/merchant-memory/stats | Stats |
| POST | /api/ai/merchant-memory/extract | Extract |
| GET | /api/ai/merchant-memory/learned-mappings | List |
| DELETE | /api/ai/merchant-memory/mapping | Delete |
| POST | /api/ai/merchant-memory/clear-all | Clear |

### Training

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/ai/training/dataset | Export dataset |
| POST | /api/ai/training/backfill-enhanced | Enhanced backfill |
| POST | /api/ai/training/categorize-uncategorized | Auto-categorize |
| GET | /api/ai/training/merchant-map | Merchant map |

---

## AI Categories Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/ai-categories/accept-single | Accept one |
| POST | /api/ai-categories/accept-batch | Accept multiple |
| GET | /api/ai-categories/metrics | Metrics |
| POST | /api/ai-categories/preview-batch | Preview |
| POST | /api/ai-categories/categorize-transactions | Get suggestions |
| GET | /api/ai-categories/suggestions-status/{id} | Status |
| POST | /api/ai-categories/auto-categorize-uncategorized | Auto-categorize |
| POST | /api/ai-categories/categorize-all | Categorize all |
| GET | /api/ai-categories/category-coverage | Coverage |

---

## Intelligence Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/intelligence/insights | AI insights |
| GET | /api/intelligence/health | Financial health |
| GET | /api/intelligence/behavior | Spending behavior |
| POST | /api/intelligence/feed | Intelligence feed |
| POST | /api/intelligence/recurring/detect | Recurring AI |
| POST | /api/intelligence/transfers/suggest | Transfer AI |
| GET | /api/intelligence/rules/suggest | Rule suggestions |
| GET | /api/intelligence/subscriptions | Subscriptions |

---

## Admin Endpoints

### Data Management

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/admin/data/stats | Statistics |
| POST | /api/admin/data/optimize | Optimize DB |
| POST | /api/admin/data/delete-transactions | Delete filtered |
| POST | /api/admin/data/reset-ai | Clear AI fields |
| POST | /api/admin/data/delete-all | Delete all |
| POST | /api/admin/data/backup | Create backup |
| GET | /api/admin/data/backup/{name} | Download backup |
| POST | /api/admin/data/restore | Restore backup |
| POST | /api/admin/data/factory-reset | Factory reset |
| POST | /api/admin/data/wipe-all | Wipe all data |

### AI Mapping

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/admin/ai-mapping | List mappings |
| POST | /api/admin/ai-mapping | Add mapping |
| DELETE | /api/admin/ai-mapping | Remove mapping |

### Backfill

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/admin/data/backfill-confidence | Backfill confidence |
| POST | /api/admin/data/backfill-merchant-names | Backfill merchants |

---

## Export Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/export/transactions.csv | Stream CSV |
| GET | /api/export/csv | Enhanced CSV |
| POST | /api/export | Export presets |

**Query Parameters:**
- `start_date`, `end_date` - Date range
- `account_id` - Filter account
- `format` - csv or parquet
- `business_only` - Business only
- `include_transfers` - Include transfers
- `include_adjustments` - Include adjustments

---

## Common Response Patterns

### Paginated Response

```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```

### Error Response

```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "request_id": "uuid"
}
```

### Job Response

```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 50,
  "total": 100
}
```

---

## Authentication

Most endpoints are unauthenticated in single-user mode. Admin endpoints check for admin token when configured:

```
Authorization: Bearer <token>
```

---

## Rate Limiting

Default rate limits via slowapi:
- General: 1000 requests/minute
- Bulk import: 10 requests/minute
- AI endpoints: Variable

---

*Generated by Claude Code Audit - December 27, 2025*
