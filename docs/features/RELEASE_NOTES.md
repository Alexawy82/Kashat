# LedgerLoop v1.1 — P2P Pipeline Simplification

## Highlights
- Simplified P2P detection pipeline - single responsibility (detect people, not recurring)
- Multi-layer filtering: internal transfers, fees, autopay, PayPal businesses
- New People & Transfers UI hub with counterparty management
- Removed duplicate auto-recurring creation from P2P (handled by Recurring Pipeline)

## Backend Changes
- Removed 370+ lines of duplicated auto-recurring code from P2P detection
- Removed 3 endpoints: `/api/p2p/auto-recurring`, `/api/p2p/auto-recurring/{id}`, `/api/p2p/correlate`
- Added autopay filtering patterns (Citi Autopay, Rocket Money, Albert Genius, etc.)
- Added PayPal business transaction filter (subscriptions → Recurring, not P2P)
- Expanded KNOWN_BUSINESSES list (gaming, SaaS, VPN services)
- Fixed stale counterparty transaction counts

## Frontend Changes
- Redesigned `/transfers` page as People & Transfers hub
- Two tabs: People (counterparties) and Internal Transfers
- Counterparty cards with sent/received stats, service icons
- Detail sheet with aliases, merge capability, transaction history
- Simplified pipeline button: Detect → Enrich (removed auto-recurring step)

## Data Quality
- Final result: 165 P2P transactions (down from 388 after filtering)
- 9 clean counterparties (all real people/transfers)
- Services breakdown: Zelle (77), Venmo (45), CashApp (24), PayPal (12), WU (5), Wire (2)

## Architecture
- Clear separation: P2P Pipeline → who you transact with
- Clear separation: Recurring Pipeline → what happens regularly
- No more duplicate recurring creation paths

---

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
- Data Management: new Settings subsection for import runs — list runs/files/periods, bulk upload, reprocess runs, and delete runs. Ingest page now supports bulk uploads.

Compatibility
- All new UI is behind a feature flag; when OFF, legacy behavior remains.

Performance
- In-process caching for analytics endpoints (120s TTL) for warm responses <=300ms.

Ops
- Start script passes the feature flag to Next.js. Artifacts for setup/start/verify are stored in artifacts/.

Rollback Plan
- Toggle feature flag OFF (LEDGERLOOP_UI_V1_COMPLETE / NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE).
- Revert commits in branch feat/ui-completion-and-endpoints if needed.
