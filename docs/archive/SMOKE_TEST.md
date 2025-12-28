# Smoke Test: Core Finance Loop (No AI, No Auth)

This script validates the core local flow:
import -> detect -> analytics -> export

## Prerequisites

- Backend running locally (default: `http://127.0.0.1:8000`)
- Python deps installed (requests/httpx from `requirements.txt`)
- No AI, realtime, or auth required

## Start the Backend

From repo root, pick one:

```bash
make run-backend
```

or:

```bash
PYTHONPATH=apps/backend/src uvicorn ledgerloop.api.main:app --reload --port 8000
```

## Verify Backend Health

```bash
curl http://127.0.0.1:8000/api/health
```

Expected: JSON with `status` and component details.

## Run

```bash
python scripts/smoke_test.py
```

## Environment Overrides

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEDGERLOOP_SMOKE_API` | `http://127.0.0.1:8000/api` | Base API URL |
| `LEDGERLOOP_SMOKE_FIXTURE` | `data/fixtures/sample_bank.csv` | CSV fixture path |
| `LEDGERLOOP_SMOKE_ACCOUNT_ID` | unset | Optional account id for import |

Example:

```bash
LEDGERLOOP_SMOKE_API=http://localhost:8000/api \
LEDGERLOOP_SMOKE_FIXTURE=data/fixtures/sample_bank.csv \
python scripts/smoke_test.py
```

## Expected Output

```
LedgerLoop Smoke Test
- API base: http://127.0.0.1:8000/api
- Fixture: /path/to/data/fixtures/sample_bank.csv
Import: run_id=... inserted=... deduped=... raw=...
Detect: zelle=... income=... adjustments=...
Analytics: income=... spend=... net=...
Export: content-type=text/csv; charset=utf-8 columns=id,account_id,posted_at,...
PASS smoke test (no AI, no realtime, no auth)
```

## Troubleshooting

- `FAIL import: ... connection refused` -> backend not running or wrong base URL.
- `FAIL import: Backend not running...` -> start the backend using the command above.
- `FAIL export: Unexpected CSV header` -> export endpoint mismatch or upstream change.
- `FAIL ... 404` -> check `LEDGERLOOP_SMOKE_API` and confirm `/api/*` paths are available.
- `FAIL analytics: ... did not return JSON` -> check backend logs for errors.
- `Fixture not found` -> verify `LEDGERLOOP_SMOKE_FIXTURE` path and that the file exists.
