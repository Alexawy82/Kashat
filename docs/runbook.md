Runbook

Common Tasks
- Start API (dev): `export PYTHONPATH=apps/backend/src && uvicorn ledgerloop.api.main:app --reload`
- Import CSV: `curl -F file=@data/fixtures/sample_bank.csv http://localhost:8000/api/imports/csv`
- List transactions: `curl 'http://localhost:8000/api/transactions?limit=20'`

Rules & Categories
- Create category: `curl -X POST http://localhost:8000/api/categories -H 'Content-Type: application/json' -d '{"name":"Coffee"}'`
- Create rule: `curl -X POST http://localhost:8000/api/rules -H 'Content-Type: application/json' -d '{"priority":1,"predicate":{"description_regex":"starbucks","amount_max":0},"action":{"assign_category_id":"<cat_id>"}}'`
- Apply rule: `curl -X POST http://localhost:8000/api/rules/<rule_id>/apply`

Transfers
- Suggest: `curl -X POST 'http://localhost:8000/api/transfers/suggest?max_days=3&amount_tolerance=0.01'`
- Review: `curl 'http://localhost:8000/api/transfers?status=pending'`
- Confirm: `curl -X POST http://localhost:8000/api/transfers/confirm -H 'Content-Type: application/json' -d '{"left_tx_id":"<A>","right_tx_id":"<B>"}'`

P2P Cashouts (Zelle/Venmo/Cash App/WU)
- Detect + persist tags/fields: `curl -X POST 'http://localhost:8000/api/detect/p2p?commit=true'`
- Summary (grouped): `curl 'http://localhost:8000/api/p2p/summary?limit=50'`
- Drilldown (one group): `curl 'http://localhost:8000/api/p2p/transactions?provider=western_union&counterparty=%28unknown%29&limit=50'`
- Manual counterparty override (e.g. WU): `curl -X PATCH 'http://localhost:8000/api/transactions/<tx_id>' -H 'Content-Type: application/json' -d '{"p2p_counterparty":"<name>"}'`

Recurring
- Suggest: `curl -X POST 'http://localhost:8000/api/recurring/suggest?min_occurrences=3&tol=0.02'`
- Review: `curl 'http://localhost:8000/api/recurring?status=pending'`
- Confirm: `curl -X POST http://localhost:8000/api/recurring/confirm -H 'Content-Type: application/json' -d '{"series_id":"<id>"}'`

Analytics & Export
- Monthly summary: `curl 'http://localhost:8000/api/analytics/monthly'`
- Category monthly: `curl 'http://localhost:8000/api/analytics/category-monthly'`
- Merchants: `curl 'http://localhost:8000/api/analytics/merchants?limit=20'`
- Export CSV: `curl -OJ 'http://localhost:8000/api/export/transactions.csv'`

AI
- Provider health: `curl http://localhost:8000/api/ai/ping`
- Smart suggestions: `curl http://localhost:8000/api/ai/suggestions/smart-categories/<tx_id>`
- Enhance uncategorized (bulk): `curl -X POST http://localhost:8000/api/ai/enhance/uncategorized`
- List jobs: `curl http://localhost:8000/api/ai/bulk-jobs`
- Job status: `curl http://localhost:8000/api/ai/bulk-job/<job_id>`
- Cancel job: `curl -X POST http://localhost:8000/api/ai/bulk-job/<job_id>/cancel`
- Retry job: `curl -X POST http://localhost:8000/api/ai/bulk-job/<job_id>/retry`

PDF Import (BoA)
- Upload: `curl -F file=@bank/eStmt_2025-01-10.pdf http://localhost:8000/api/imports/pdf`
- Generate BoA goldens: `python3 scripts/boa_goldens_generate.py` (writes `data/fixtures/*.csv`)
- BoA tests: `PYTHONPATH=apps/backend/src python3 -m unittest apps/backend/tests/test_boa_goldens.py -v`

Audit Logs
- Query logs: `curl 'http://localhost:8000/api/audit/logs?limit=50'`
- Auth
  - Authentication is currently disabled (single-user mode). Do not expose the service to untrusted networks.

- Lifespan
  - Startup/shutdown handled by application lifespan. Avoid starting multiple backends against the same DB to prevent DuckDB lock conflicts.
