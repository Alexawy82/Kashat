# LedgerLoop UI → Backend API Map

This maps the **features visible in the frontend** to the **FastAPI endpoints** they depend on, plus any relevant feature flags.

## Global Conventions

- Frontend calls `apiRequest('/x')` → `GET/POST /api/x` (same-origin `/api/*` proxied by Next).
- Metrics scrape uses `GET /metrics` (Prometheus text format).
- **Auth is disabled**: treat all endpoints as accessible to anyone who can reach the service.

## Pages

### `/` Dashboard

- Core dashboard analytics + KPIs: `GET /api/analytics/dashboard`, `GET /api/analytics/summary`
- Charts: `GET /api/analytics/monthly`, `GET /api/analytics/category-monthly`, `GET /api/analytics/cashflow`, `GET /api/analytics/merchants`
- AI-assisted insights (optional): `GET /api/analytics/ai/dashboard-summary`, `GET /api/analytics/ai/trends`, `GET /api/analytics/ai/spending-patterns`
- Merchant memory stats: `GET /api/ai/merchant-memory/stats`

### `/transactions` Transactions

- List/search/filter: `GET /api/transactions`, `GET /api/transactions/stats`
- Batch fetch (used by Transfers UI v1): `POST /api/transactions/batch`
- Assign category: `POST /api/transactions/{tx_id}/category`
- AI suggestions:
  - Smart category suggestions: `GET /api/ai/suggestions/smart-categories/{transaction_id}`
  - Apply smart category: `POST /api/ai/suggestions/apply-smart-category`
  - Opt-out merchant/category combo: `POST /api/ai/suggestions/opt-out`
  - Auto-create category: `POST /api/ai/categories/auto-create`
  - AI categories batch review: `POST /api/ai-categories/preview-batch`, `POST /api/ai-categories/accept-batch`
  - Bulk enhance uncategorized: `POST /api/ai/enhance/uncategorized`

### `/import` Import

- Upload (single file): `POST /api/imports/csv`, `POST /api/imports/pdf`
- Upload (bulk): `POST /api/imports/bulk`
- AI processing status polling: `GET /api/imports/{run_id}/ai-analysis`
- Suggested rules: `POST /api/imports/suggest-rules`

### `/settings/data-management` Data Management (UI v1)

**Flag:** `NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE=1` (frontend gate)

- List runs: `GET /api/imports/runs`
- Run details: `GET /api/imports/runs/{run_id}/files`, `GET /api/imports/runs/{run_id}/summary`
- Delete run: `DELETE /api/imports/runs/{run_id}`
- Reprocess run: `POST /api/imports/runs/{run_id}/reprocess`
- Bulk upload: `POST /api/imports/bulk`
- Accounts dropdown: `GET /api/accounts`
- Detection utilities:
  - Zelle: `POST /api/detect/zelle`
  - Income: `POST /api/detect/income`
  - Adjustments: `POST /api/detect/adjustments`

### `/rules` Rules

- List/create: `GET /api/rules`, `POST /api/rules`
- Preview matches: `POST /api/rules/preview`
- Apply: `POST /api/rules/{rule_id}/apply`
- Import/Export: `POST /api/rules/import`, `GET /api/rules/export`

### `/categories` Categories

- List/create: `GET /api/categories`, `POST /api/categories`
- Merge: `POST /api/categories/merge`
- Backend also supports delete: `DELETE /api/categories/{category_id}` (UI currently doesn’t call it)

### `/transfers` Transfers

- Suggest pairs: `POST /api/transfers/suggest_v2`
- List pairs: `GET /api/transfers?status=pending|confirmed`
- Confirm/reject: `POST /api/transfers/confirm`, `POST /api/transfers/reject`
- Include/exclude from analytics: `POST /api/transfers/group/{group_id}/analytics?include=true|false`
- Optional UI v1 optimization (batch tx details): `POST /api/transactions/batch`

### `/recurring` Recurring

- Suggest: `POST /api/recurring/suggest`
- List: `GET /api/recurring?status=pending|confirmed`
- Confirm/reject: `POST /api/recurring/confirm`, `POST /api/recurring/reject`
- Series transactions sparkline: `GET /api/recurring/{series_id}/transactions`

### `/export` Export

- Classic CSV export: `GET /api/export/transactions.csv`
- Preset export (csv/parquet): `POST /api/export`
- UI v1 CSV export: `GET /api/export/csv`
- Export history (via audit log): `GET /api/audit/logs?entity_type=export&action=export:csv&limit=5`

### `/audit` Audit

- Query logs: `GET /api/audit/logs`

### `/settings` Settings + Admin Tools

- App settings: `GET /api/settings`, `POST /api/settings`
- AI provider ping: `GET /api/ai/ping`
- Data admin (destructive):
  - Stats: `GET /api/admin/data/stats`
  - Optimize: `POST /api/admin/data/optimize`
  - Backup: `POST /api/admin/data/backup`, download `GET /api/admin/data/backup/{name}`
  - Restore: `POST /api/admin/data/restore`
  - Reset AI fields: `POST /api/admin/data/reset-ai`
  - Delete transactions: `POST /api/admin/data/delete-transactions`
  - Delete all: `POST /api/admin/data/delete-all`
  - Factory reset: `POST /api/admin/data/factory-reset`
  - Wipe all: `POST /api/admin/data/wipe-all`
- AI category mapping panel: `GET/POST/DELETE /api/admin/ai-mapping`

### `/pulse` System Pulse

- Detailed health: `GET /api/health/detailed`
- AI status: `GET /api/ai/status`
- Import runs: `GET /api/imports/runs`
- Data stats: `GET /api/admin/data/stats`
