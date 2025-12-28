# LedgerLoop Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                      │
├─────────────────────────────────────────────────────────────────┤
│ Pages: Ingest | Transactions | Analytics | Rules | Categories   │
│ Components: Import Wizard | Charts | Review Queue | Settings    │
│ Services: API Client | WebSocket | Workflow | Validation        │
└─────────────────────────────────────────────────────────────────┘
                                   │ HTTP/WS
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│ Routes: /import | /transactions | /analytics | /rules          │
│ Middleware: CORS | Auth | Metrics | WebSocket                  │
│ Background: Real-time Processing | AI Workflows                │
└─────────────────────────────────────────────────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
    │   Parser    │         │ Classifier  │         │  Analytics  │
    │   Service   │         │   Service   │         │   Service   │
    ├─────────────┤         ├─────────────┤         ├─────────────┤
    │ PDF/CSV     │         │ Rules Eng.  │         │ DuckDB SQL  │
    │ BoA Parser  │         │ AI (Local)  │         │ Aggregation │
    │ Balance Val │         │ Category    │         │ Insights    │
    │ Normalize   │         │ Transfer    │         │ Export      │
    │ Dedupe      │         │ Recurring   │         │ Reporting   │
    └─────────────┘         └─────────────┘         └─────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │     Local AI Stack      │
                      ├─────────────────────────┤
                      │ LM Studio / OpenAI API  │
                      │ Category Mapping        │
                      │ Confidence Scoring      │
                      │ Merchant Extraction     │
                      └─────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Storage Layer (DuckDB)                      │
├─────────────────────────────────────────────────────────────────┤
│ Core: transactions | accounts | categories | rules             │
│ Import: import_run | import_file | raw_record                  │
│ Analysis: match_transfer | recurring_series | event_log       │
│ AI: ai_bulk_job | ai_workflow_run | ai_category_mapping        │
└─────────────────────────────────────────────────────────────────┘
```

## Page Inventory

| Route | Purpose | Data Dependencies | API Calls |
|-------|---------|------------------|-----------|
| `/` | Dashboard with overview analytics | transactions, categories, insights | `/api/analytics/summary`, `/api/transactions` |
| `/ingest` | File upload and import workflow | import runs, AI analysis | `/api/imports/csv`, `/api/imports/pdf` |
| `/transactions` | Transaction list with filters/bulk ops | transactions, categories, rules | `/api/transactions`, `/api/categories` |
| `/categories` | Category hierarchy management | categories, transaction counts | `/api/categories` |
| `/rules` | Rule builder and preview | rules, preview transactions | `/api/rules`, `/api/rules/preview` |
| `/transfers` | People & Transfers hub - counterparties and internal transfers | P2P stats, counterparties, transfer pairs | `/api/p2p/*`, `/api/transfers` |
| `/recurring` | Subscription and recurring analysis | recurring series, next dates | `/api/recurring` |
| `/analytics` | Advanced charts and insights | aggregated data, trends | `/api/analytics/*` |
| `/export` | Data export in multiple formats | filtered transactions | `/api/export` |
| `/audit` | Activity log and change history | event log entries | `/api/audit` |
| `/detect` | Zelle/income/adjustment detection | transaction flags | `/api/detect/*` |
| `/settings` | App configuration and AI settings | settings, AI mappings | `/api/settings` |
| `/ai` | AI processing status and controls | AI jobs, workflow runs | `/api/ai/*` |
| `/live` | Real-time dashboard | live metrics, WebSocket | `/api/realtime`, WebSocket |

## API Inventory

### Core Operations
| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|

## Sequence Diagrams

### Recurring Flow

User → Web: POST /api/recurring/suggest
Web → Backend: detect, insert series, return pending list
User → Web: POST /api/recurring/confirm (bulk)
Web → Backend: update series status, write audit

### Transfers Flow

User → Web: POST /api/transfers/suggest_v2
Web → Backend: detect descriptor-based pairs, insert with group_id
User → Web: POST /api/transfers/confirm or /reject (bulk by group)
Web → Backend: update decided_at, write audit; toggle include via group analytics

### P2P Detection Flow

User → Web: POST /api/p2p/detect {use_ai: true}
Web → Backend: scan transactions, filter (fees, autopay, internal), extract counterparties
Backend → Backend: normalize names, fuzzy match to existing counterparties
Backend → DB: upsert counterparty, insert p2p_transaction links
User → Web: POST /api/p2p/enrich
Web → Backend: AI classifies unclassified counterparties (person vs business)
User → Web: GET /api/p2p/counterparties
Web → Backend: return counterparties with stats (sent, received, tx count)

### Data Management Flow

User → Web: POST /api/imports/bulk (multipart)
Web → Backend: create run, files, rows; optional background processing
User → Web: GET runs/files/summary
Web → Backend: aggregate metrics; reprocess or delete actions update state and emit logs
| GET | `/api/health` | System status | - | `{status, version, db_stats}` |
| GET | `/api/transactions` | List transactions | query filters | `TransactionItem[]` |
| POST | `/api/transactions/{id}/category` | Assign category | `{category_id}` | success |
| GET | `/api/categories` | List categories | - | `CategoryItem[]` |
| POST | `/api/categories` | Create category | `{name, parent_id?}` | `CategoryItem` |

### Import Pipeline
| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/imports/csv` | Upload CSV file | `FormData{file, enable_ai?}` | `{run_id, inserted, duplicates}` |
| POST | `/api/imports/pdf` | Upload PDF statement | `FormData{file, enable_ai?}` | `{run_id, inserted, duplicates}` |
| GET | `/api/imports/runs` | List import history | `limit?` | `ImportRun[]` |
| GET | `/api/imports/{run_id}/ai-analysis` | Get AI analysis status | - | `{analysis_complete, stats}` |

### Classification & Rules
| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/rules` | List rules | - | `Rule[]` |
| POST | `/api/rules` | Create rule | `{predicate, action, priority}` | `Rule` |
| POST | `/api/rules/preview` | Preview rule matches | `{predicate}` | `{matches: TransactionItem[]}` |
| POST | `/api/transfers/detect` | Run transfer detection | `{method?, days?}` | `{pairs, stats}` |
| GET | `/api/recurring` | List recurring series | - | `RecurringSeries[]` |

### Analytics & Insights
| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/analytics/summary` | Overview metrics | `from?, to?` | `{total_spent, categories, trends}` |
| GET | `/api/analytics/monthly` | Monthly breakdowns | `from?, to?` | `MonthlyData[]` |
| GET | `/api/analytics/merchants` | Top merchants | `limit?` | `MerchantData[]` |
| GET | `/api/export/csv` | Export transactions CSV | query filters | CSV stream |
| GET | `/api/audit` | Activity log | `from?, to?, limit?` | `EventLog[]` |

### AI & Real-time
| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| POST | `/api/ai/categorize` | AI categorization | `{tx_ids}` | `{job_id}` |
| GET | `/api/ai/jobs/{id}` | Job status | - | `{status, progress, results}` |
| GET | `/api/realtime/metrics` | Live metrics | - | `{active_users, recent_imports}` |
| WS | `/api/realtime/ws` | WebSocket feed | - | real-time events |

## Service Inventory

### Core Services
- **ParseService**: PDF/CSV parsing with bank-specific parsers (BoA supported)
- **NormalizationService**: Deterministic description cleaning and date parsing
- **DeduplicationService**: Fingerprint-based duplicate prevention
- **ValidationService**: Running balance checks and anomaly detection

### Classification Services
- **RulesEngine**: Predicate-action rule execution with priority ordering
- **AIService**: Local LLM integration with confidence scoring and caching
- **TransferMatcher**: Automated transfer pair detection (2 algorithms)
- **RecurringDetector**: Subscription and recurring payment identification
- **P2PDetector**: Person-to-person transfer detection with counterparty tracking (Zelle, Venmo, CashApp, PayPal, Wire, Western Union)

### Analytics Services
- **AnalyticsEngine**: DuckDB-powered aggregation and reporting
- **InsightsService**: Trend analysis and spending pattern detection
- **ExportService**: Multi-format data export (CSV, Parquet)
- **AuditLogger**: Complete change tracking and event logging

#### Recent Additions (flagged by LEDGERLOOP_UI_V1_COMPLETE)
- API: `GET /api/analytics/summary` — unified totals + breakdowns with 120s cache.
- API: `GET /api/analytics/predictions` — heuristic budget risk/savings/recurring with explanations and 120s cache.
- API: `GET /api/export/csv` — streaming CSV export, `Content-Disposition` filename includes date range, logs `export:csv` to `event_log`.
- Frontend: `useAnalyticsSummary()` and `useAnalyticsPredictions()` hooks; `/export` page wired to new CSV export and shows export history from audit log.
- Data Management: import runs/files tracking with `transaction_ingest` mapping. Endpoints: `/api/import/runs`, `/api/import/runs/{run_id}/files`, `/summary`, `DELETE /runs/{run_id}`, `POST /runs/{run_id}/reprocess`, and bulk uploads via `POST /api/import/bulk`.

### Background Services
- **RealtimeProcessor**: WebSocket event broadcasting
- **WorkflowEngine**: Multi-step AI processing workflows
- **BulkJobProcessor**: Batch operation handling

## Data Flow

```
Upload → Parse → Normalize → Validate → Dedupe → Persist → Classify → Insights → UI
   │        │        │         │         │        │         │         │        │
   │        │        │         │         │        │         │         │        └─ Display
   │        │        │         │         │        │         │         └─ Analytics
   │        │        │         │         │        │         └─ Rules + AI
   │        │        │         │         │        └─ Database
   │        │        │         │         └─ Fingerprint check
   │        │        │         └─ Balance validation
   │        │        └─ Description normalization
   │        └─ Bank-specific parsing
   └─ File checksum + metadata
```

## Local AI Integration

**AI Provider Chain**: Local heuristics → LM Studio/OpenAI → Confidence escalation

**Classification Pipeline**:
1. Rule engine (deterministic, fast)
2. Cached AI results (by description signature)
3. Local LLM call (if confidence < threshold)
4. Category mapping to local taxonomy

**Privacy Guarantees**:
- All PII stays local (no external API calls with sensitive data)
- Configurable AI provider (local-only mode available)
- Audit trail for all AI decisions

## Storage Schema

### Core Entities
- `institution` → `account` → `transaction`
- `category` (hierarchical tree)
- `rule` (predicate + action JSON)

### Import Tracking
- `import_run` → `import_file` → `raw_record`
- Complete lineage from file to transaction
- Deterministic re-import with duplicate detection

### Analysis Tables
- `transaction_category` (many-to-many with provenance)
- `match_transfer` (paired transactions)
- `recurring_series` (subscription patterns)
- `p2p_transaction` (person-to-person transfer links)
- `counterparty` (people/businesses you transact with)
- `event_log` (audit trail)

### AI Tables
- `ai_bulk_job` (batch processing status)
- `ai_workflow_run` (multi-step workflows)
- `ai_category_mapping` (provider → local categories)

## Security & Privacy

- **Authentication**: Optional bearer tokens (admin + general API)
- **CORS**: Configurable origins (dev-friendly default)
- **PII Protection**: No sensitive data in logs
- **Local-First**: All data in local DuckDB file
- **AI Privacy**: Local LLM option, external calls require explicit opt-in

## Observability

- **Structured Logging**: JSON logs with request IDs
- **Metrics**: Prometheus endpoints for monitoring
- **Real-time**: WebSocket for live updates
- **Audit Trail**: Complete change history in event_log
- **Health Checks**: Database connectivity and system status
### Analytics Dashboard Flow

The frontend dashboard consumes a composite API `GET /api/analytics/dashboard`, which aggregates:
- Summary (`/analytics/summary`)
- Monthly and Category Monthly (`/analytics/monthly`, `/analytics/category-monthly`)
- Merchants (`/analytics/merchants`)
- Cashflow (`/analytics/cashflow`)
- AI sections when enabled (`/analytics/ai/dashboard-summary`, `/analytics/ai/trends`)

This consolidates multiple calls into a single round‑trip while reusing server‑side logic.

### Categories Lifecycle (Delete/Merge)

- `DELETE /api/categories/{id}`: Allowed only when no children and no transaction references.
- `POST /api/categories/merge`: Moves all transaction references from `from_id` to `to_id`, then deletes `from_id`. Merging a parent into a child is blocked to avoid cycles.
- Both operations log to `event_log` for auditability.
