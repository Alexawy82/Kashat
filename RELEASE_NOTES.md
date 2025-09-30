# LedgerLoop v1.0 — UI Completion + Analytics/Export Endpoints

Highlights
- New: analytics summary and predictions endpoints (cached).
- New: streaming CSV export with audit logging and date-based filename.
- New: React hooks (useAnalyticsSummary/useAnalyticsPredictions) and export history UI.
- New: Confidence chip and lineage badge on transactions (flagged).
- New: Feature flag LEDGERLOOP_UI_V1_COMPLETE to toggle new UI/flows.

Backend
- Added GET /api/analytics/summary (totals, byMonth, byCategory, topMerchants).
- Added GET /api/analytics/predictions (budgetRisk, savingsOps, recurringForecast) with explanations.
- Added GET /api/export/csv (streaming, logs export:csv to event_log).
- Updated OpenAPI spec with new routes and schemas.

Frontend
- Added NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE feature flag with graceful fallback.
- New hooks: useAnalyticsSummary/useAnalyticsPredictions with memoization and manual invalidation.
- Export page wired to new CSV endpoint and shows last 5 export events.
- Transactions show AI confidence chip and a lineage badge.

Compatibility
- All new UI is behind a feature flag; when OFF, legacy behavior remains.

Performance
- In-process caching for analytics endpoints (120s TTL) for warm responses <=300ms.

Ops
- Start script passes the feature flag to Next.js. Artifacts for setup/start/verify are stored in artifacts/.

Rollback Plan
- Toggle feature flag OFF (LEDGERLOOP_UI_V1_COMPLETE / NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE).
- Revert commits in branch feat/ui-completion-and-endpoints if needed.
