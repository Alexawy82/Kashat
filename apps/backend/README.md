Backend (FastAPI + DuckDB)

Run (dev):
- Ensure Python 3.11+
- `pip install fastapi uvicorn duckdb python-dotenv python-multipart`
- `export PYTHONPATH=apps/backend/src`
- `uvicorn ledgerloop.api.main:app --reload`

Environment vars:
- `LEDGERLOOP_DATA_DIR` — directory for DB and uploads (default: `~/.ledgerloop`)

Endpoints:
- `GET /api/health` — health and paths
- `GET /api/transactions` — list transactions with filters (includes category)
- `POST /api/transactions/{tx_id}/category` — assign category manually
- `PATCH /api/transactions/{tx_id}` — update flags (is_business, is_adjustment, is_income)
- `POST /api/imports/csv` — upload CSV to import
- `POST /api/imports/pdf` — upload PDF; auto-detects BoA (boa_v2025) and ingests
- `GET /api/categories` / `POST /api/categories` — manage categories
- `GET /api/rules` / `POST /api/rules` — manage rules
- `POST /api/rules/preview` — preview predicate matches
- `POST /api/rules/{id}/apply` — apply rule to matching transactions
- `POST /api/transfers/suggest` — scan and save transfer suggestions
- `POST /api/transfers/suggest_v2` — descriptor-based pairing for Online Banking transfers
- `GET /api/transfers?status=pending|confirmed|all` — list transfer pairs
- `POST /api/transfers/confirm` — confirm a transfer pair
- `POST /api/transfers/reject` — reject a pending suggestion
- `POST /api/transfers/group/{group_id}/analytics?include=true|false` — toggle include in analytics for a confirmed group
- `POST /api/recurring/suggest` — scan and save recurring candidates
- `GET /api/recurring?status=pending|confirmed|rejected|all` — list recurring series
- `POST /api/recurring/confirm` — confirm a series
- `POST /api/recurring/reject` — reject a series
- `GET /api/analytics/monthly` — monthly spend/income/net summary
- `GET /api/analytics/dashboard` — aggregated dashboard (period comparisons, KPIs, top merchants/categories, optional AI)
- `GET /api/analytics/category-monthly` — spend by category over months
- `GET /api/analytics/merchants` — top merchants by spend
- `GET /api/analytics/cashflow` — totals with adjustments/transfers excluded
- `GET /api/analytics/recurring` — series with next_date and price_hike
- `GET /api/export/transactions.csv` — CSV export of normalized transactions
- `POST /api/export` — export presets (csv|parquet) with flags
- `GET /api/audit/logs` — query audit log entries
- `POST /api/detect/zelle/run` — tag transactions with Zelle direction
- `POST /api/detect/income` — detect income (biweekly/payroll); `?commit=true` to persist
- `POST /api/detect/adjustments` — detect adjustments (cashback/reversals); `?commit=true` to persist
- `GET /api/settings` / `POST /api/settings` — get/set simple settings (recurring tolerance)

Notes:
- The database and tables are created automatically on first run.
- CSV expects headers like: `date,description,amount` or `date,description,credit,debit,currency`.
- Transfers are detected by opposite-sign, near-zero-net pairs within N days; similarity of descriptions influences score.
- Recurring series are detected from description + amount clusters with weekly/monthly cadence heuristics.
- PDF parsing: BoA parser (boa_v2025) is table-first with text fallback, extracts period, account last4, opening/closing balances, and validates running balance; requires `pdfplumber`.

BoA Goldens
- Independent goldens: place CSVs in `data/fixtures/boa_goldens/eStmt_*.csv` with headers `date,description,amount[,balance]`.
- Generate provisional CSVs from your PDFs in `bank/*.pdf`: `python3 scripts/boa_goldens_generate.py`
- Tests compare parser rows vs independent goldens (≥99% capture) in `apps/backend/tests/test_boa_goldens.py`.
- If `pdfplumber` is missing:
  - `python3 -m venv .venv && . .venv/bin/activate && pip install pdfplumber`
  - Run scripts/tests with `.venv/bin/python` or activate the venv.

Determinism
- `make determinism-check` runs 3 randomized passes and compares DB logical hashes; returns non-zero on mismatch.
