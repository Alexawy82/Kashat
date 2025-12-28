# LedgerLoop Testing Map

A comprehensive guide to all application pipelines, data flows, and test scenarios.

---

## 1. CORE DATA PIPELINES

### A) PDF Import Pipeline

```
Entry Point: POST /api/import/pdf
            POST /api/import/bulk (multiple files)
```

**Steps:**
1. **Upload** → `apps/backend/src/ledgerloop/api/routes/imports.py:371-400`
   - Receive PDF file via FastAPI UploadFile
   - Validate file type and size

2. **Parse** → `apps/backend/src/ledgerloop/ingest_pdf.py:20-138`
   - Attempt BoA parser first (`parse.banks.boa_v2025`)
   - Fallback to SimpleBankV1 text extraction via pdfplumber
   - Extract: date, description, amount

3. **Normalize** → `apps/backend/src/ledgerloop/normalization.py:12-16`
   - `normalize_description()`: lowercase, collapse whitespace, trim punctuation
   - `parse_date()`: multiple format support (YYYY-MM-DD, MM/DD/YYYY, etc.)
   - `parse_amount()`: handle credit/debit columns

4. **Fingerprint** → `apps/backend/src/ledgerloop/dedup.py:7-9`
   - Generate SHA1 hash: `{account_id}|{date}|{amount}|{description_norm}`

5. **Deduplicate** → Check fingerprint unique constraint in database
   - If duplicate: increment `deduped` counter, skip insert
   - If new: insert into `transaction` table

6. **Link to Import Run** → Insert into `transaction_ingest`
   - Track which run/file created each transaction

7. **Background AI Processing** → `_process_import_with_workflow()`
   - If `enable_ai=True`, queue background task

**Tables Affected:**
- `import_run` (INSERT)
- `import_file` (INSERT)
- `transaction` (INSERT)
- `transaction_ingest` (INSERT)
- `raw_record` (optional, for audit)

**Exit Point:**
```json
{
  "run_id": "uuid",
  "file_id": "uuid",
  "inserted": 45,
  "deduped": 3,
  "raw": 48,
  "hash": "sha256",
  "ai_processing": true
}
```

---

### B) CSV Import Pipeline

```
Entry Point: POST /api/import/csv
            POST /api/import/bulk
```

**Steps:**
1. **Upload** → `apps/backend/src/ledgerloop/api/routes/imports.py:339-368`
2. **Parse** → `apps/backend/src/ledgerloop/ingest_csv.py:34-146`
   - Read CSV with DictReader
   - Support flexible headers (date/Date/DATE, etc.)
3. **Normalize** → Same as PDF
4. **Fingerprint** → Same as PDF
5. **Store Raw** → Insert each row to `raw_record` for audit trail
6. **Deduplicate & Insert** → Same as PDF
7. **Background AI** → Same as PDF

**Tables Affected:** Same as PDF plus `raw_record`

---

### C) Transaction Classification Pipeline

```
Entry Point: POST /api/transactions/{tx_id}/category (manual)
            POST /api/rules/{rule_id}/apply (rule-based)
            Background: AI Workflow after import
```

**Classification Hierarchy (Priority Order):**

1. **Manual Assignment** → User assigns category via UI
   - `apps/backend/src/ledgerloop/api/routes/transactions.py:232-270`
   - Triggers merchant memory learning

2. **Rule Application** → `apps/backend/src/ledgerloop/api/routes/rules.py:124-170`
   - Predicate matching: description_regex, amount_min/max, sign
   - Action: assign_category_id, set_business, payee_alias

3. **AI Fallback** → Multiple layers:
   - **Enhanced Categorization** → `ai_enhanced_categorization.py`
   - **Smart Categorization** → `ai_smart_categorization.py`
   - **Base AI Service** → `ai.py` (Local heuristics or OpenAI/LM Studio)

**AI Classification Flow:**
```
Transaction Description
        ↓
┌───────────────────────────┐
│ Merchant Category Map     │ (regex patterns → category)
│ e.g. NETFLIX → Entertainment
└───────────────────────────┘
        ↓ (if no match)
┌───────────────────────────┐
│ Category Keywords Match   │ (keyword lists per category)
│ e.g. "coffee" → Food & Dining
└───────────────────────────┘
        ↓ (if no match)
┌───────────────────────────┐
│ AI Category Mapping       │ (ai_category_mapping table)
│ Provider label → Local ID
└───────────────────────────┘
        ↓ (if no match)
┌───────────────────────────┐
│ OpenAI/LM Studio Call     │ (if configured)
│ JSON response parsing
└───────────────────────────┘
```

**Tables Affected:**
- `transaction_category` (INSERT/UPDATE)
- `event_log` (INSERT - audit)
- `merchant_memory` (UPDATE - learning)

---

### D) Transfer Detection Pipeline

```
Entry Point: POST /api/transfers/suggest
            POST /api/transfers/suggest-v2
```

**V1 Algorithm** → `apps/backend/src/ledgerloop/transfers.py:33-82`
- Criteria:
  - Different accounts
  - Opposite signs (one credit, one debit)
  - Amount sum within tolerance (default ±$0.01)
  - Posted within ±3 days
  - Jaccard similarity of descriptions
- Score: 50% time proximity + 50% description similarity
- Threshold: score >= 0.5

**V2 Algorithm** → `apps/backend/src/ledgerloop/transfers.py:116-167`
- Parse descriptor patterns:
  - "online banking transfer from/to sav/chk XXXX"
  - Match pairs where one is "from" and one is "to"
  - Same last4 digits, opposite signs

**Tables Affected:**
- `match_transfer` (INSERT)
- `event_log` (INSERT on confirm/reject)

**User Actions:**
- `POST /api/transfers/confirm` → Set decided_at, create group_id
- `POST /api/transfers/reject` → Delete suggestion

---

### E) Recurring Detection Pipeline

```
Entry Point: POST /api/recurring/suggest
```

**Algorithm** → `apps/backend/src/ledgerloop/recurring.py:51-115`

1. **Group Transactions** by description + amount bucket (±2% tolerance)
2. **Calculate Intervals** between consecutive transactions
3. **Detect Cadence** from median interval:
   - 6-8 days → weekly
   - 13-15 days → biweekly
   - 28-31 days → monthly
4. **Compute Confidence** based on:
   - Number of occurrences
   - Interval stability
   - Amount stability
5. **Detect Price Hikes** → Last amount > previous by >10%

**Tables Affected:**
- `recurring_series` (INSERT)
- `recurring_tx` (INSERT - link transactions to series)

**User Actions:**
- `POST /api/recurring/{id}/confirm` → Set status='confirmed'
- `POST /api/recurring/{id}/reject` → Set status='rejected'

---

### F) Category Management Pipeline

```
Entry Point: POST /api/categories (create)
            POST /api/categories/merge (merge)
            DELETE /api/categories/{id} (delete)
```

**Create Flow** → `apps/backend/src/ledgerloop/api/routes/categories.py:28-54`
1. Check for exact name match (case-insensitive)
2. Try AI-aware dedup (fuzzy matching, synonyms)
3. If no match, create new category

**Merge Flow** → `apps/backend/src/ledgerloop/api/routes/categories.py:102-156`
1. Validate both categories exist
2. Prevent merging parent into child (cycle detection)
3. Move all `transaction_category` references
4. Update `ai_category_mapping` references
5. Delete source category

**Delete Flow:**
- Block if has children
- Block if referenced by transactions
- Only delete orphan categories

**Tables Affected:**
- `category` (INSERT/DELETE)
- `transaction_category` (UPDATE on merge)
- `ai_category_mapping` (UPDATE on merge)
- `event_log` (INSERT)

---

### G) Export Pipeline

```
Entry Point: GET /api/export/csv
            GET /api/export/transactions.csv
            POST /api/export (CSV/Parquet)
```

**Steps** → `apps/backend/src/ledgerloop/api/routes/export.py`

1. **Build Query** with filters:
   - Date range (from/to)
   - Business only flag
   - Include/exclude transfers
   - Include/exclude adjustments

2. **Join Tables:**
   - transaction
   - transaction_category → category (names)
   - match_transfer (transfer status)
   - recurring_tx (recurring series ID)

3. **Stream Response:**
   - CSV: StreamingResponse with chunked writes
   - Parquet: PyArrow table conversion

**Tables Read:**
- `transaction`
- `transaction_category`
- `category`
- `match_transfer`
- `recurring_tx`

**Audit:**
- `event_log` (INSERT with action='export:csv')

---

## 2. AI WORKFLOWS

### A) AI Categorization Flow

```
┌─────────────────┐
│ Transaction     │
│ description,    │
│ amount          │
└────────┬────────┘
         ↓
┌─────────────────────────────────────────────┐
│ LocalAIService.suggest_categories()         │
│ apps/backend/src/ledgerloop/ai.py:280-365   │
│                                             │
│ 1. Check merchant_category_map (regex)      │
│ 2. Detect income/transfer/zelle patterns    │
│ 3. Match category_keywords                  │
│ 4. Return top 3 suggestions with confidence │
└────────┬────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ CategoryMatcher.find_exact_matches()        │
│ ai_categories.py:81-97                      │
│                                             │
│ Match AI suggestion name to existing        │
│ category names (case-insensitive)           │
└────────┬────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ CategoryMatcher.find_fuzzy_matches()        │
│ ai_categories.py:99-141                     │
│                                             │
│ SequenceMatcher similarity + keyword overlap│
│ Threshold: 0.8                              │
└────────┬────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ Auto-apply if confidence >= threshold       │
│ (default: 0.7)                              │
│                                             │
│ Insert into transaction_category            │
│ Log to event_log                            │
└─────────────────────────────────────────────┘
```

### B) Merchant Memory/Learning Flow

```
User manually categorizes transaction
                ↓
┌─────────────────────────────────────────────┐
│ learn_from_transaction_categorization()     │
│ ai_smart_categorization.py                  │
│                                             │
│ 1. Extract merchant name from description   │
│ 2. Upsert to merchant_memory table:         │
│    - merchant_name                          │
│    - category_id                            │
│    - usage_count++                          │
│    - last_used_at                           │
└────────┬────────────────────────────────────┘
         ↓
Future transactions from same merchant
get automatic category suggestion
```

### C) Smart Suggestions Flow

```
┌─────────────────────────────────────────────┐
│ suggest_smart_categories()                  │
│ ai_categories.py:180-260                    │
│                                             │
│ 1. Get AI suggestions from provider         │
│ 2. Find exact matches in category table     │
│ 3. Find fuzzy matches                       │
│ 4. Find parent category matches             │
│ 5. Suggest new category if confidence > 0.7 │
│ 6. Return SmartCategorySuggestion[]         │
└─────────────────────────────────────────────┘
```

### D) Bulk Enhancement Flow (Import Workflow)

```
POST /api/import/* with enable_workflow=true
                ↓
┌─────────────────────────────────────────────┐
│ AIWorkflowEngine.process_import_workflow()  │
│ ai_workflow.py:72-173                       │
│                                             │
│ Stage 1: IMPORT - Get transactions          │
│ Stage 2: AI_ENHANCEMENT - Batch process     │
│ Stage 3: RULE_APPLICATION - Auto-categorize │
│ Stage 4: DUPLICATE_DETECTION - Find dupes   │
│ Stage 5: QUALITY_VALIDATION - Score results │
│ Stage 6: COMPLETION - Store results         │
└────────┬────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│ AIImportProcessor.process_import_batch()    │
│ ai_import.py:57-101                         │
│                                             │
│ For each transaction:                       │
│ - Categorize with enhanced AI               │
│ - Get merchant info                         │
│ - Check for anomalies                       │
│ - Calculate quality score                   │
│                                             │
│ Analyze patterns for rule suggestions       │
└─────────────────────────────────────────────┘
```

---

## 3. DATA DEPENDENCIES

### Dependency Graph

```
                    ┌──────────────┐
                    │ institution  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   account    │
                    └──────┬───────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼────┐          ┌──────▼───────┐        ┌────▼─────┐
│ import │          │  transaction │        │ category │
│  run   │          │              │        │          │
└───┬────┘          └──────┬───────┘        └────┬─────┘
    │                      │                     │
    │               ┌──────┴────────────────┐    │
    │               │                       │    │
    │         ┌─────▼─────┐          ┌──────▼────▼──────┐
    │         │   rule    │          │ transaction_     │
    │         │           │          │   category       │
    │         └───────────┘          └──────────────────┘
    │
┌───▼────────┐    ┌─────────────┐    ┌──────────────────┐
│import_file │    │match_transfer│    │recurring_series │
└────────────┘    └─────────────┘    └──────────────────┘
```

### Feature Dependencies

| Feature | Requires |
|---------|----------|
| View Transactions | `transaction` table has data |
| Categorize Transaction | `category` table has categories |
| Apply Rules | `rule` table has rules, `category` exists |
| Transfer Detection | ≥2 accounts with transactions |
| Recurring Detection | ≥3 similar transactions |
| Analytics Dashboard | `transaction` data |
| AI Categorization | `category` table, AI config |
| Export | `transaction` data |

### New User Required Operations Order

```
1. Create/ensure account exists
   └── POST /api/import/* auto-creates if needed

2. Import transactions (CSV/PDF)
   └── POST /api/import/csv or /api/import/pdf

3. Create categories (if not using defaults)
   └── POST /api/categories
   └── Or use seed categories from schema.sql

4. Create rules (optional)
   └── POST /api/rules

5. Run transfer detection (optional)
   └── POST /api/transfers/suggest

6. Run recurring detection (optional)
   └── POST /api/recurring/suggest

7. View analytics
   └── GET /api/analytics/dashboard
```

---

## 4. DATABASE TABLES

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `institution` | Bank/credit union | id, name |
| `account` | User account | id, institution_id, name, type, last4 |
| `transaction` | Financial transaction | id, account_id, posted_at, amount, description_norm, fingerprint, ai_* fields |
| `category` | Spending category | id, name, parent_id |
| `rule` | Classification rule | id, priority, predicate_json, action_json |

### Import Tracking Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `import_run` | Import session | id, started_at, source, ai_* tracking |
| `import_file` | Uploaded file | id, run_id, path, hash, type, logical_hash |
| `raw_record` | Original parsed data | id, file_id, row_no, raw_json |
| `transaction_ingest` | Links tx to import | tx_id, run_id, file_id |

### Relationship Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `transaction_category` | TX-Category link | tx_id, category_id, applied_by |
| `transaction_tag` | TX tags | tx_id, tag |
| `match_transfer` | Transfer pairs | left_tx_id, right_tx_id, score, decided_at |
| `recurring_series` | Recurring pattern | id, name, cadence, amount_mean/sd |
| `recurring_tx` | TX-Series link | series_id, tx_id |

### AI Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ai_bulk_job` | Batch processing | id, job_type, total/processed/status |
| `ai_workflow_run` | Workflow tracking | id, stages, success_rate, errors_json |
| `ai_category_mapping` | Provider→Local map | provider, source_label, category_id |
| `merchant_memory` | Learned merchants | merchant_name, category_id, usage_count |

### Audit Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `event_log` | All changes | id, entity_type, entity_id, action, payload_json, ts, actor |
| `schema_version` | Migrations | version, applied_at, description |

### Views

| View | Purpose |
|------|---------|
| `v_transaction_with_category` | TX + category name |
| `v_monthly_summary` | Monthly income/expense |

---

## 5. TEST CHECKLIST

### STANDALONE Tests (Feature in Isolation)

#### Import Tests
- [ ] CSV import with valid headers
- [ ] CSV import with alternate headers (Date vs date)
- [ ] CSV import with credit/debit columns
- [ ] PDF import (BoA format)
- [ ] PDF import (SimpleBankV1 format)
- [ ] Duplicate file detection (same hash)
- [ ] Logical hash duplicate detection
- [ ] Import creates run and file records
- [ ] Empty file handling

#### Transaction Tests
- [ ] List transactions with filters
- [ ] List transactions with sorting
- [ ] Get single transaction
- [ ] Assign category to transaction
- [ ] Delete transaction and related records
- [ ] Patch transaction flags (is_business, etc.)
- [ ] Batch get transactions by IDs

#### Category Tests
- [ ] List categories
- [ ] Create category
- [ ] Delete category (no children/refs)
- [ ] Merge categories
- [ ] Prevent delete with children
- [ ] Prevent delete with TX references
- [ ] Case-insensitive duplicate prevention

#### Rule Tests
- [ ] List rules
- [ ] Create rule with valid predicate/action
- [ ] Preview rule matches
- [ ] Apply rule to transactions
- [ ] Export/import rules
- [ ] Rule suggestions based on patterns

#### Transfer Detection Tests
- [ ] V1 heuristic matching
- [ ] V2 descriptor-based matching
- [ ] Confirm transfer pair
- [ ] Reject transfer pair
- [ ] Exclude from analytics after confirm

#### Recurring Detection Tests
- [ ] Weekly cadence detection
- [ ] Monthly cadence detection
- [ ] Biweekly cadence detection
- [ ] Price hike detection
- [ ] Confirm/reject series
- [ ] Exclude confirmed transfers from recurring

#### Analytics Tests
- [ ] Monthly summary
- [ ] Category breakdown
- [ ] Top merchants
- [ ] Cashflow calculation
- [ ] Dashboard endpoint
- [ ] Predictions endpoint

#### Export Tests
- [ ] CSV export with date range
- [ ] CSV export excluding transfers
- [ ] Parquet export (if pyarrow installed)
- [ ] Event log on export

### INTEGRATION Tests (Features Work Together)

#### Import → Classification Flow
- [ ] Import CSV → AI auto-categorizes transactions
- [ ] Import PDF → AI workflow runs
- [ ] Import → Built-in detectors (Zelle, income, adjustments)

#### Rule → Transaction Flow
- [ ] Create rule → Apply → Transactions categorized
- [ ] Rule suggestion from AI patterns → Create rule → Apply

#### Manual Category → Learning Flow
- [ ] Assign category → Merchant memory updated
- [ ] Future import → Same merchant auto-categorized

#### Transfer → Analytics Flow
- [ ] Detect transfers → Confirm → Analytics excludes
- [ ] Detect transfers → Reject → Analytics includes

#### Complete User Flow
- [ ] New account → Import → AI process → Categorize → Export

### EDGE CASES

#### Empty Data
- [ ] Empty database returns []
- [ ] Analytics with no transactions returns zeros
- [ ] Transfer detection with single account returns empty
- [ ] Recurring detection with <3 transactions returns empty

#### Duplicates
- [ ] Re-import same file skips duplicates
- [ ] Fingerprint collision handling
- [ ] Category merge with existing mappings

#### Errors
- [ ] Invalid CSV format handling
- [ ] Invalid PDF format handling
- [ ] Missing category on assign
- [ ] Missing transaction on operations
- [ ] Database constraint violations

#### Performance
- [ ] Large file import (1000+ transactions)
- [ ] Analytics with large dataset
- [ ] Bulk categorization

---

## 6. API ENDPOINT SUMMARY

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/ai/stats` | AI service status |

### Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/import/csv` | Import CSV file |
| POST | `/api/import/pdf` | Import PDF file |
| POST | `/api/import/bulk` | Import multiple files |
| GET | `/api/import/runs` | List import runs |
| GET | `/api/import/runs/{id}/files` | List run files |
| DELETE | `/api/import/runs/{id}` | Delete run and TXs |
| POST | `/api/import/runs/{id}/reprocess` | Re-run AI |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions` | List transactions |
| GET | `/api/transactions/stats` | Count/bounds |
| GET | `/api/transactions/{id}` | Get single TX |
| POST | `/api/transactions/{id}/category` | Assign category |
| PATCH | `/api/transactions/{id}` | Update flags |
| DELETE | `/api/transactions/{id}` | Delete TX |
| POST | `/api/transactions/batch` | Get by IDs |

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/categories` | List categories |
| POST | `/api/categories` | Create category |
| DELETE | `/api/categories/{id}` | Delete category |
| POST | `/api/categories/merge` | Merge categories |
| GET | `/api/categories/{id}/usage` | Usage stats |

### Rules
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rules` | List rules |
| POST | `/api/rules` | Create rule |
| POST | `/api/rules/preview` | Preview matches |
| POST | `/api/rules/{id}/apply` | Apply rule |
| GET | `/api/rules/export` | Export all rules |
| POST | `/api/rules/import` | Import rules |
| GET | `/api/rules/suggestions` | AI suggestions |

### Transfers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transfers` | List transfers |
| POST | `/api/transfers/suggest` | Run V1 detection |
| POST | `/api/transfers/suggest-v2` | Run V2 detection |
| POST | `/api/transfers/confirm` | Confirm pair |
| POST | `/api/transfers/reject` | Reject pair |

### Recurring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/recurring` | List series |
| POST | `/api/recurring/suggest` | Run detection |
| POST | `/api/recurring/{id}/confirm` | Confirm series |
| POST | `/api/recurring/{id}/reject` | Reject series |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/dashboard` | Full dashboard |
| GET | `/api/analytics/monthly` | Monthly summary |
| GET | `/api/analytics/cashflow` | Cashflow totals |
| GET | `/api/analytics/summary` | Unified summary |
| GET | `/api/analytics/predictions` | Budget predictions |
| GET | `/api/analytics/recurring` | Recurring forecast |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/csv` | Export to CSV |
| GET | `/api/export/transactions.csv` | Alt CSV export |
| POST | `/api/export` | Export with format |

---

## 7. RUNNING TESTS

### Backend Tests
```bash
cd /mnt/c/Users/Marwan/Desktop/AI/Flos
export PYTHONPATH=apps/backend/src
.venv/bin/python -m pytest apps/backend/tests -v
```

### Specific Test Files
```bash
# Import tests
.venv/bin/python -m pytest apps/backend/tests/test_ingest_golden.py -v

# Dedup tests
.venv/bin/python -m pytest apps/backend/tests/test_dedup.py -v

# Transfer tests
.venv/bin/python -m pytest apps/backend/tests/test_transfers*.py -v

# Recurring tests
.venv/bin/python -m pytest apps/backend/tests/test_recurring.py -v

# API smoke tests
.venv/bin/python -m pytest apps/backend/tests/test_api_smoke.py -v
```

### Manual API Testing
```bash
# Start backend
export PYTHONPATH=apps/backend/src
.venv/bin/python -m uvicorn ledgerloop.api.main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/transactions?limit=5
curl http://localhost:8000/api/categories
curl http://localhost:8000/api/analytics/dashboard
```

---

*Generated: 2025-12-15*
