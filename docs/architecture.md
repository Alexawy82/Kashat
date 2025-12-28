Architecture Overview

- Local-first: DuckDB single-file DB under `LEDGERLOOP_DATA_DIR` (default `~/.ledgerloop/ledgerloop.duckdb`).
- Backend: FastAPI serving REST endpoints and static docs.
- Storage: Deterministic ingestion with lineage and audit log.
- Analytics: Parameterized DuckDB SQL views.
- Frontend: Next.js consuming local API.

AI Provider Layer
- `ai.AIService` is the single gateway for AI calls (local heuristics, LM Studio via OpenAI-compatible base_url, or OpenAI).
- Per-task models and thresholds, confidence-based escalation, and caching are supported.
- All categorization and anomaly features route through AIService, then map to local categories.

Realtime
- Real-time analytics performs local heuristics first; if confidence is low, it escalates to the configured AI provider with a small TTL cache to avoid duplicate calls.

Key Modules
- `db`: manages DuckDB connection and schema initialization.
- `ingest_csv`: parses CSV files to raw records and normalized transactions.
- `normalization`: deterministic parsing/normalization utilities.
- `dedup`: fingerprinting + lookup to avoid duplicates.
- `api.routes`: FastAPI routers for health, transactions, imports, AI endpoints, realtime, etc.

Determinism & Audit
- Import runs and files are recorded with hashes and timestamps.
- Raw rows are kept as JSON in `raw_record` for reproducibility.
- Transactions store a computed `fingerprint` used for idempotency.
