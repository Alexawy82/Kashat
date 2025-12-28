# UI Page-by-Page Review (Production Readiness)

This is a **user-facing** review: what each page presents, what value it adds, how it connects to backend/AI pipelines, and what needs tightening for a polished production app (**no auth**, so safety is network-based).

Reference for route mapping: `docs/qa/FEATURE_API_MAP.md`.

## Principles for “production ready” (no auth)

- Pages must not show “fake green” states. If a feature is disabled by flags or missing routes, the UI must say so clearly.
- No randomness in user-visible analytics (deterministic output only).
- Clear “next action” when empty (first-run experience).
- Avoid full page reloads for refresh; prefer in-app refresh.
- Feature flags should gate navigation/entry points (avoid dead pages).
- Destructive actions must be clearly marked and require explicit confirmation.

## Page: `/` Dashboard

**What user sees**
- KPI cards: total tx, total volume, categorized %, AI processed %, income/spend/surplus for chosen range.
- Charts + “predictive” widgets: cashflow forecast, spending patterns, insights.
- AI system panel: AI processed count, anomalies, uncategorized warning.
- “Merchant Memory” stats.
- Time range selector + refresh.

**Primary value**
- One place to answer “Where is my money going?” and “What should I do next?” (uncategorized, anomalies, trends).

**Backend/AI dependencies**
- Core analytics: `/api/analytics/dashboard`, `/api/analytics/monthly`, `/api/analytics/category-monthly`, `/api/analytics/cashflow`, `/api/analytics/merchants`.
- Predictive widgets: `/api/analytics/predictive/*`, `/api/analytics/predictions`.
- AI stats: `/api/ai/merchant-memory/stats`.

**Pipeline integration**
- Import → transactions → analytics.
- AI enrichment (import workflow + bulk jobs) improves “AI processed %”, merchant normalization, and suggestions.

**Polish / QA notes**
- Must stay consistent across widgets for the selected range (avoid mixing stale analytics vs selected range).
- First-run empty state should drive user to `/import`.

## Page: `/transactions` Transactions

**What user sees**
- Search/filter + large list (virtualized).
- Category assignment, bulk actions, AI suggestions/acceptance flows.

**Backend/AI dependencies**
- Core: `/api/transactions`, `/api/transactions/stats`, `/api/categories`.
- Category assignment: `/api/transactions/{tx_id}/category`.
- AI suggestions + actions: `/api/ai/suggestions/*`, `/api/ai/categories/auto-create`, `/api/ai-categories/*`.
- Bulk AI job: `/api/ai/enhance/uncategorized`, `/api/ai/bulk-job/*`.

**Pipeline integration**
- Main “workbench” for cleaning data after import.

**Polish / QA notes**
- Needs crisp empty states + clear “what changed” feedback after bulk actions.
- Confirm that any long-running AI actions show progress and don’t block UI.

## Page: `/import` Import

**What user sees**
- Upload CSV/PDF/bulk, optional AI processing, AI status polling, suggested rule creation.

**Backend/AI dependencies**
- `/api/imports/csv`, `/api/imports/pdf`, `/api/imports/bulk`
- AI analysis polling: `/api/imports/{run_id}/ai-analysis`
- Suggested rules: `/api/imports/suggest-rules`
- Rule creation: `/api/rules`

**Pipeline integration**
- “Entry point” for the whole system: imports produce runs → transactions → analytics → rules.

**Polish / QA notes**
- Upload errors should be user-friendly (especially 413 “upload too large”).
- Provide guidance on supported PDFs (BoA) and expected CSV format.

## Page: `/settings/data-management` Data Management (UI v1)

**What user sees**
- Import runs history, run details, reprocess/delete, bulk upload, detection utilities.

**Backend dependencies**
- `/api/imports/runs*`, `/api/accounts`, `/api/detect/*`

**Pipeline integration**
- Operational controls: rerun AI workflows, clean up runs, run detection.

**Polish / QA notes**
- This page is gated by `NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE`; ensure nav/links don’t push users here unless enabled.

## Page: `/rules` Rules

**What user sees**
- List rules, create rule, preview matches, apply, import/export seed rules.

**Backend dependencies**
- `/api/rules*`, `/api/categories`

**Pipeline integration**
- Rules are the “automation layer” that stabilizes categorization after initial cleanup.

**Polish / QA notes**
- Preview/apply must clearly communicate scope (how many transactions will change).

## Page: `/categories` Categories

**What user sees**
- Category tree, create/edit, merge utility, delete (when safe).

**Backend dependencies**
- `/api/categories`, `/api/categories/merge`, `/api/categories/{id}/usage`, `DELETE /api/categories/{id}`

**Pipeline integration**
- Categories drive analytics aggregation and rule actions.

**Polish / QA notes**
- Deleting categories should be blocked when “in use”; steer user to Merge.

## Page: `/transfers` Transfers

**What user sees**
- Suggested transfer pairs, approve/reject, bulk actions, analytics include toggle.

**Backend dependencies**
- `/api/transfers*`, plus `/api/transactions/batch` for UI v1 detail rendering

**Pipeline integration**
- Transfer classification affects “real spend” analytics (transfers should generally be excluded).

## Page: `/recurring` Recurring

**What user sees**
- Suggested recurring series, approve/reject, bulk actions, sparkline per series.

**Backend dependencies**
- `/api/recurring*`

**Pipeline integration**
- Enables forecasts and “upcoming obligations” style insights.

## Page: `/export` Export

**What user sees**
- One-click exports + advanced export controls + optional history.

**Backend dependencies**
- `/api/export`, `/api/export/transactions.csv`, `/api/export/csv`, `/api/audit/logs`

## Page: `/settings` Settings + Admin Tools

**What user sees**
- App settings (AI provider config, thresholds, realtime toggle) plus destructive admin operations (backup/restore/delete/wipe).

**Backend dependencies**
- `/api/settings`, `/api/ai/ping`, `/api/admin/*`, `/api/admin/ai-mapping`

**Production warning**
- With auth disabled, `/api/admin/*` must only be reachable via trusted network.

## Page: `/pulse` System Pulse

**What user sees**
- System health cards, AI status, import activity, basic system stats.

**Backend dependencies**
- `/api/health/detailed`, `/api/ai/status`, `/api/imports/runs`, `/api/admin/data/stats`
