# UI Completion Plan — LedgerLoop

This plan inventories current routes and API usage, then tracks tasks to complete UI wiring and the 3 missing backend endpoints. All new UI/behavior is guarded by the feature flag `LEDGERLOOP_UI_V1_COMPLETE` (frontend uses `NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE`).

## Sitemap (App Router)

Discovered Next.js routes (apps/web/src/app):

- `/` (Dashboard)
- `/transactions`
- `/rules`
- `/transfers`
- `/recurring`
- `/detect`
- `/export`
- `/audit`
- `/ai`
- `/metrics`
- `/settings`
- `/ingest`
- `/live`
- `/status`
- `/categories`
- `/demo`
- `/test-components`

## Current API Usage (frontend)

Detected API calls in web (best-effort grep):

- `/analytics/monthly`
- `/analytics/category-monthly`
- `/analytics/merchants`
- `/analytics/cashflow`
- `/analytics/ai/dashboard-summary`
- `/analytics/ai/trends`
- `/analytics/ai/spending-patterns`
- `/analytics/predictions` (currently POST in SharedAnalyticsService)
- `/transactions`
- `/transactions/{transaction_id}/category`
- `/categories`
- `/import/csv`, `/import/pdf`, `/import/runs`
- `/rules`, `/rules/preview`
- `/transfers`
- `/recurring`
- `/audit`
- `/realtime/*` (WebSocket connect + health/analytics live)

Notes:
- Export page currently relies on existing `/export/transactions.csv` endpoint; new GET `/export/csv` will be added to match spec.
- Analytics predictions are referenced as `/analytics/predictions` via POST in code; we will add GET and keep POST compatible (non‑breaking) if present.

## OpenAPI vs Web Usage (high level)

New endpoints to add per Objective:

- GET `/api/analytics/summary`
- GET `/api/analytics/predictions`
- GET `/api/export/csv`

These are not present or not fully wired in the backend; UI will consume them behind the feature flag.

## Gaps and Actions

Backend endpoints (Step 1):

- [x] `GET /api/analytics/summary` with params: `from`, `to`, `includeTransfers=false`; returns: `totals{income,spend,net}`, `byMonth[]`, `byCategory[]`, `topMerchants[]`. Add 120s in‑process cache keyed by params. Respect `includeTransfers`.
- [x] `GET /api/analytics/predictions` with params: `from`, `to`; returns: `budgetRisk[]`, `savingsOps[]`, `recurringForecast[]`, with explanations. Deterministic heuristics on fixtures.
- [x] `GET /api/export/csv` with params: `from`, `to`, `onlyBusiness=false`, `includeTransfers=false`; streaming CSV with `content-disposition` including date range; log `export:csv` to `event_log`.
- [x] Update `openapi.yaml` with the above and regenerate client types if used.
- [x] Tests: unit + integration as specified (see Testing section below).

Frontend wiring (Steps 2–4):

- [ ] Add feature flag plumbing: respect `NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE` (default OFF in prod) and `LEDGERLOOP_UI_V1_COMPLETE` env for backend emitted behavior.
- [ ] Hooks: `useAnalyticsSummary()` and `useAnalyticsPredictions()` with internal memoization and invalidation on events.
- [ ] Update Dashboard/Analytics components to use the hooks when flag ON; gracefully degrade to existing code when OFF.
- [ ] `/export` page: call `GET /api/export/csv`, toast on success, add Export History (last 5 entries) using `event_log` (or `exports` table if present; we’ll use `event_log`).

Transactions “workbench” (Step 3):

- [ ] Confidence chip (e.g., “97% — merchant+desc”) using `ai_confidence_score` if available; degrade to hidden when flag OFF or missing.
- [ ] Lineage badge per row (source file name; hover for file/page/row if available via `raw_record`/`import_file`).
- [ ] Bulk actions: Reclassify, Exclude from analytics, Export selection (batch calls). All behind flag.

Detect page (Step 4):

- [ ] Convert actions to Preview → Apply: modal preview with sample results, then Apply with progress UI; emit success events.

Event‑driven refresh (Step 5):

- [ ] Standardize WS topics: `analytics/updated`, `transactions/updated`, `patterns/updated`.
- [ ] Emit topics on ingest/classify/rules/apply/detect/export completion (backend); subscribe in frontend and invalidate caches in `useAnalytics*`, transactions table, and patterns views.

Rules Wizard (Step 6):

- [ ] 4‑step wizard with condition builder → preview → action → confirm; optional “apply now”.
- [ ] Ensure CRUD endpoints all exist; add thin handlers only if missing.

Transfers & Recurring (Step 7):

- [ ] Transfers side‑by‑side pairs with approve/reject/exclude and “Approve All Safe”.
- [ ] Recurring table with columns: Merchant | Avg Amount | Cadence | Next Due | Confidence | Approve.
- [ ] Hook to existing detection endpoints; add finalize endpoints if only preview exists.

Settings polish (Step 8):

- [ ] Double‑confirm destructive actions; optional DB backup/export button before reset.

Metrics/Admin (Step 9, optional):

- [ ] Surface counters like `files_processed_total`, `classify_latency_ms_avg`, `analytics_cache_hits`.

## Testing Plan Additions

Backend:

- [ ] Unit: analytics summary query shaping, cache behavior; predictions deterministic outputs on golden fixtures.
- [ ] Integration: export streaming (text/csv, filename), analytics correctness under known fixtures; warm vs cold latency budgets.

Frontend:

- [ ] Hooks tests for `useAnalyticsSummary` and `useAnalyticsPredictions` (memoization + invalidation).
- [ ] Component tests: confidence chips, lineage badges, rule wizard flow, detect preview/apply.
- [ ] Simple e2e: upload → analytics → export (reuse existing infra if present).

## Docs to Update (in this branch)

- [ ] `ARCHITECTURE.md`: analytics facade, event topics, export flow.
- [ ] `openapi.yaml`: new routes + schemas.
- [ ] `TEST_PLAN.md`: new tests + manual checks for wizard and previews.
- [ ] `UI_COMPLETION_PLAN.md`: keep checklist updated.

## Release

- PR: “UI Completion + Analytics/Export Endpoints (No Regression)”
- Include artifacts links (setup/start/verify logs), screenshots/GIFs, rollback plan (feature flag + commits list).
