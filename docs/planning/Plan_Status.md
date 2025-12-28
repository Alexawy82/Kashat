Execution Plan Update (backend + tests) — see also docs/runbook.md

Completed (this iteration)
- Transfers v2: ±1 day pairing, group_id, analytics exclusion; confirm sets group id; tests for similarity.
- Zelle detection: descriptor parsing (to/from), tagging endpoint; unit tests.
- Recurring tuning: cadence windows incl. biweekly, price-hike flag; tests.
- Income/Adjustments: heuristics and tagging (is_income/is_adjustment); tests.
- Transactions API: filters (date, category, business, include_transfers), PATCH for flags; audit logged.
- Analytics: monthly, category-monthly, merchants, cashflow totals.
- Exports: GET CSV + POST presets (csv/parquet) with flags.
- Determinism harness v2: randomized ordering/chunking/restarts, logical DB hash.

New in this pass
- BoA parser robustness: month-name period parsing; opening/closing balance validation; auto-fingerprint.
- Independent goldens harness: expects CSVs at `data/fixtures/boa_goldens/*.csv` with row/amount diffs on failure.
- Transfers v2 descriptor pairing endpoint: `POST /api/transfers/suggest_v2` with deterministic `group_id`.
- Zelle persistence: `zelle_direction`, `zelle_counterparty` columns; exposed in API/export and set by `/api/detect/zelle/run`.
- Recurring persistence: `last_date`, `next_date`, `price_hike`; analytics endpoint exposes next_date.
- Detection endpoints: `/api/detect/income` and `/api/detect/adjustments` with dry-run/commit.
- Determinism v2.1: multi-run (3) hash comparison; Make `determinism-check` target.

Pending (need inputs or separate sprint)
- BoA PDF parser boa_v2025: Implemented; independent goldens harness in place; consider manual review of CSVs.
- Golden fixtures set: independent CSVs under `data/fixtures/boa_goldens`; wire into CI; reconcile diffs as needed.
- Frontend V1 UX: bulk edit, rule editor, subscriptions cards, transfer groups UI.
- LLM adapter + cache: behind toggle; network + provider keys required.
- Security baseline + CI pipeline; synthetic scale data generator.
