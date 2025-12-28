# LedgerLoop Architecture Deep Dive

A comprehensive technical guide to how LedgerLoop processes, classifies, and analyzes financial transactions.

---

## Table of Contents
1. [Data Model](#1-data-model)
2. [Logic Layers](#2-logic-layers)
3. [Intelligence Layer](#3-intelligence-layer)
4. [State Machines](#4-state-machines)
5. [Integration Points](#5-integration-points)
6. [Configuration & Settings](#6-configuration--settings)
7. [Audit & Lineage](#7-audit--lineage)

---

## 1. Data Model

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    CORE ENTITIES                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────────────────────────────┐
│  institution │──1:N──│   account    │──1:N──│            transaction               │
├──────────────┤       ├──────────────┤       ├──────────────────────────────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)                              │
│ name         │       │ institution_id│      │ account_id (FK)                      │
│ bic          │       │ name         │       │ posted_at                            │
│ routing_aba  │       │ type         │       │ amount                               │
│ website      │       │ mask         │       │ currency                             │
│ created_at   │       │ currency     │       │ description_norm                     │
└──────────────┘       │ balance      │       │ external_id                          │
                       │ last_sync    │       │ fingerprint (UNIQUE)                 │
                       │ is_active    │       │ source_raw_id                        │
                       │ created_at   │       │ ai_category_suggestion               │
                       └──────────────┘       │ ai_merchant_name                     │
                                              │ ai_confidence                        │
                                              │ zelle_direction                      │
                                              │ zelle_counterparty                   │
                                              │ is_business                          │
                                              │ is_income                            │
                                              │ is_adjustment                        │
                                              │ created_at                           │
                                              └──────────────────────────────────────┘
                                                            │
                    ┌───────────────────┬──────────────────┼──────────────────┬───────────────────┐
                    │                   │                  │                  │                   │
                    ▼                   ▼                  ▼                  ▼                   ▼
        ┌───────────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
        │transaction_category│  │ match_transfer │  │ recurring_tx │  │transaction_  │  │   event_log      │
        ├───────────────────┤  ├───────────────┤  ├──────────────┤  │   ingest     │  ├──────────────────┤
        │ tx_id (FK)        │  │ id (PK)       │  │ tx_id (FK)   │  ├──────────────┤  │ id (PK)          │
        │ category_id (FK)  │  │ left_tx_id    │  │ series_id    │  │ tx_id (FK)   │  │ entity_type      │
        │ applied_by        │  │ right_tx_id   │  │ occurrence   │  │ run_id (FK)  │  │ entity_id        │
        │ applied_at        │  │ confidence    │  │ expected_at  │  │ file_id (FK) │  │ action           │
        │ confidence        │  │ method        │  │ confirmed    │  └──────────────┘  │ payload_json     │
        └───────────────────┘  │ decided_at    │  └──────────────┘                    │ ts               │
                │              │ decided_by    │         │                            │ actor            │
                │              └───────────────┘         │                            └──────────────────┘
                ▼                                        ▼
        ┌──────────────┐                        ┌────────────────┐
        │   category   │                        │recurring_series│
        ├──────────────┤                        ├────────────────┤
        │ id (PK)      │                        │ id (PK)        │
        │ name         │◄──self-referencing     │ merchant_pattern│
        │ parent_id    │   (hierarchy)          │ amount_low     │
        │ is_system    │                        │ amount_high    │
        │ sort_order   │                        │ cadence        │
        └──────────────┘                        │ last_seen      │
                                                │ next_expected  │
                                                │ confidence     │
                                                │ is_active      │
                                                └────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  IMPORT PIPELINE                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  import_run  │──1:N──│ import_file  │──1:N──│  raw_record  │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ started_at   │       │ run_id (FK)  │       │ file_id (FK) │
│ completed_at │       │ path         │       │ line_number  │
│ source       │       │ hash         │       │ content_json │
│ user_note    │       │ type         │       │ status       │
│ status       │       │ row_count    │       │ error_message│
│ error_message│       │ created_at   │       │ created_at   │
└──────────────┘       └──────────────┘       └──────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   RULES ENGINE                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│        rule          │
├──────────────────────┤
│ id (PK)              │
│ name                 │
│ predicate_json       │  ──► {"description_regex": "STARBUCKS"}
│ action_json          │  ──► {"set_category": "uuid-of-category"}
│ priority             │
│ is_active            │
│ created_at           │
│ updated_at           │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 AI/ML SUBSYSTEM                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────┐
│ merchant_category_mapping│     │     ai_bulk_job         │     │   ai_workflow_run   │
├─────────────────────────┤     ├─────────────────────────┤     ├─────────────────────┤
│ id (PK)                 │     │ id (PK)                 │     │ id (PK)             │
│ merchant_pattern        │     │ job_type                │     │ workflow_type       │
│ category_id (FK)        │     │ status                  │     │ status              │
│ confidence              │     │ total_items             │     │ started_at          │
│ source                  │     │ processed_items         │     │ completed_at        │
│ created_at              │     │ error_count             │     │ config_json         │
│ last_used_at            │     │ started_at              │     │ result_json         │
│ use_count               │     │ completed_at            │     │ error_message       │
└─────────────────────────┘     │ result_json             │     └─────────────────────┘
                                └─────────────────────────┘

┌─────────────────────────┐
│   ai_category_mapping   │
├─────────────────────────┤
│ id (PK)                 │
│ ai_category_name        │
│ system_category_id (FK) │
│ confidence              │
│ created_at              │
│ updated_at              │
└─────────────────────────┘
```

### Key Relationships

| Parent | Child | Relationship | Description |
|--------|-------|--------------|-------------|
| `institution` | `account` | 1:N | Bank holds multiple accounts |
| `account` | `transaction` | 1:N | Account contains transactions |
| `transaction` | `transaction_category` | 1:N | Transaction can have multiple categories |
| `category` | `category` | Self-ref | Hierarchical categories (parent_id) |
| `transaction` | `match_transfer` | 1:2 | Transfer links two transactions |
| `recurring_series` | `recurring_tx` | 1:N | Series contains occurrences |
| `import_run` | `import_file` | 1:N | Run processes multiple files |
| `import_file` | `transaction_ingest` | 1:N | File produces transactions |

### Deduplication Strategy

Transactions are deduplicated using a **fingerprint** - a SHA1 hash of:
```python
fingerprint = SHA1(f"{account_id}|{posted_at}|{abs(amount):.2f}|{description_norm}")
```

The `fingerprint` column has a UNIQUE constraint, preventing duplicate imports.

---

## 2. Logic Layers

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                      │
│  Next.js Frontend (apps/web)  │  FastAPI REST API (apps/backend/src/ledgerloop/api) │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ANALYTICS LAYER                                         │
│     analytics.py: Summary aggregations, predictions, caching (120s TTL)             │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DETECTION LAYER                                         │
│  transfers.py: Transfer detection (V1 heuristic, V2 descriptor parsing)             │
│  recurring.py: Recurring pattern detection (cadence analysis)                        │
│  dedup.py: Fingerprint-based deduplication                                          │
│  ai_dedup.py: AI-enhanced fuzzy duplicate detection                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CLASSIFICATION LAYER                                    │
│  rules.py: Rule-based auto-categorization                                           │
│  ai_categories.py: Smart category matching (exact, fuzzy, parent)                   │
│  ai.py: AI-powered categorization (local heuristics → LM Studio → OpenAI)          │
│  merchant_memory: Learn from user corrections                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              INGESTION LAYER                                         │
│  ingest_pdf.py: PDF parsing (BoA v2025, SimpleBankV1 fallback)                      │
│  parse/banks/: Bank-specific parsers                                                 │
│  normalization.py: Description normalization, date parsing                          │
│  db.py: Database connection, schema management                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                           │
│                         DuckDB (Thread-local connections)                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Ingestion Layer

**Purpose**: Parse raw financial data into normalized transactions

**Entry Points**:
- `POST /imports/upload` - Bulk file upload (CSV, PDF)
- `POST /imports/pdf` - PDF statement upload
- `POST /imports/csv` - CSV upload

**Processing Pipeline**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Raw File   │────▶│   Parser    │────▶│ Normalizer  │────▶│  Dedup      │
│  (PDF/CSV)  │     │  Selection  │     │             │     │  Check      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                          │                    │                   │
                          ▼                    ▼                   ▼
                    ┌───────────┐        ┌───────────┐       ┌───────────┐
                    │BoA v2025  │        │normalize_ │       │fingerprint│
                    │SimpleBankV1│       │description│       │ = SHA1()  │
                    │CSV Generic│        │parse_date │       │           │
                    └───────────┘        └───────────┘       └───────────┘
                                                                   │
                                                                   ▼
                                                             ┌───────────┐
                                                             │INSERT into│
                                                             │transaction│
                                                             │(or skip)  │
                                                             └───────────┘
```

**Key Functions** (`ingest_pdf.py:20-138`):
```python
def import_pdf_upload(file_bytes, filename, account_id, run_id, file_id):
    # 1. Create import_run record
    # 2. Try BoA parser first
    # 3. Fallback to SimpleBankV1 text parsing
    # 4. For each transaction:
    #    - Normalize description
    #    - Generate fingerprint
    #    - INSERT (skip on constraint violation = duplicate)
    # 5. Return stats: {inserted, deduped, raw, parser}
```

**Normalization** (`normalization.py`):
- Uppercase conversion
- Punctuation removal
- Whitespace collapsing
- Common prefix stripping (POS, DEBIT, etc.)

### 2.2 Classification Layer

**Purpose**: Assign categories to transactions

**Classification Methods** (in priority order):

| Priority | Method | Source | Confidence |
|----------|--------|--------|------------|
| 1 | User Manual | User action | 1.0 |
| 2 | Rule Match | rules.py | 0.95 |
| 3 | Merchant Memory | merchant_category_mapping | Varies |
| 4 | AI Suggestion | ai.py | 0.6-0.95 |
| 5 | Default | None | 0.0 |

**Rule Engine** (`rules.py`):
```python
# Predicate Types:
{
    "description_regex": "STARBUCKS|SBUX",  # Regex match
    "amount_min": 10.0,                      # Minimum amount
    "amount_max": 100.0                      # Maximum amount
}

# Action Types:
{
    "set_category": "uuid-category-id",
    "set_business": true,
    "set_income": true
}
```

**Category Matching** (`ai_categories.py:81-178`):
1. **Exact Match**: Case-insensitive name comparison
2. **Fuzzy Match**: SequenceMatcher ratio > 0.8, keyword overlap
3. **Parent Match**: Map to parent category (e.g., "Starbucks" → "Food & Dining")

### 2.3 Detection Layer

**Purpose**: Identify patterns and relationships

**Transfer Detection** (`transfers.py`):
```
┌─────────────┐                              ┌─────────────┐
│ Transaction │    Amount Match              │ Transaction │
│  Account A  │◄───(-$500 ↔ +$500)──────────▶│  Account B  │
│  -$500.00   │    Time Window (7 days)      │  +$500.00   │
└─────────────┘                              └─────────────┘
        │                                           │
        └───────────► match_transfer ◄──────────────┘
                      (left_tx_id, right_tx_id)
```

**V1 (Heuristic)**:
- Match opposite amounts within 7-day window
- Boost confidence for Zelle, ACH keywords

**V2 (Descriptor Parsing)**:
- Parse structured transfer descriptors
- Extract counterparty names
- Match by reference numbers

**Recurring Detection** (`recurring.py:45-150`):

```python
def detect_recurring_candidates(account_id, days_back=180):
    # 1. Group transactions by normalized description
    # 2. Bucket by amount (±10% tolerance)
    # 3. Analyze intervals between occurrences
    # 4. Detect cadence: weekly(7d), biweekly(14d), monthly(28-31d)
    # 5. Score confidence based on:
    #    - Occurrence count (≥3 required)
    #    - Interval stability (stddev)
    #    - Amount stability
    # 6. Create recurring_series and recurring_tx records
```

**Cadence Detection**:
| Interval (days) | Cadence | Tolerance |
|-----------------|---------|-----------|
| 5-9 | weekly | ±2 days |
| 12-18 | biweekly | ±4 days |
| 26-35 | monthly | ±5 days |
| 355-375 | yearly | ±10 days |

### 2.4 Analytics Layer

**Purpose**: Aggregate and predict financial patterns

**Caching Strategy** (`analytics.py`):
```python
_CACHE_TTL_SECONDS = 120.0  # 2-minute cache

# Cache key: (endpoint, account_id, date_range)
# Invalidated on: transaction insert/update, category change
```

**Summary Aggregations**:
```json
{
  "totals": {
    "income": 15000.00,
    "expenses": 12000.00,
    "net": 3000.00,
    "transactionCount": 1602
  },
  "byMonth": [...],
  "byCategory": [...],
  "topMerchants": [...]
}
```

**Prediction Models**:
- **Budget Risk**: Compare current spending to historical averages
- **Savings Opportunities**: Identify reducible recurring expenses
- **Recurring Forecast**: Project future bills based on detected patterns

### 2.5 Presentation Layer

**API Routes** (`api/__init__.py`):

| Route Module | Prefix | Purpose |
|--------------|--------|---------|
| `health` | `/health` | System health checks |
| `transactions` | `/transactions` | CRUD operations |
| `imports` | `/imports` | File upload, run management |
| `categories` | `/categories` | Category CRUD |
| `rules` | `/rules` | Rule management |
| `transfers` | `/transfers` | Transfer detection/confirmation |
| `recurring` | `/recurring` | Recurring detection |
| `analytics` | `/analytics` | Aggregations, predictions |
| `export` | `/export` | CSV/Parquet export |
| `audit` | `/audit` | Event log queries |
| `detect` | `/detect` | Zelle detection |
| `settings` | `/settings` | Configuration |
| `admin` | `/admin` | Administrative operations |
| `accounts` | `/accounts` | Account management |
| `ai` | `/ai` | AI operations |
| `ai_categories` | `/ai/categories` | AI category mapping |
| `ai_enhanced` | `/ai/enhanced` | Enhanced AI features |

---

## 3. Intelligence Layer

### AI Provider Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                  AIService                                           │
│                           (Coordinator/Facade)                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
            │LocalAIService │ │ LM Studio     │ │ OpenAI        │
            │(Built-in)     │ │ (Local LLM)   │ │ (Cloud)       │
            ├───────────────┤ ├───────────────┤ ├───────────────┤
            │• Pattern match│ │• localhost:   │ │• api.openai.  │
            │• Keyword rules│ │  1234         │ │  com          │
            │• Heuristics   │ │• OpenAI-compat│ │• GPT-4/3.5    │
            │• Zero latency │ │• Privacy-first│ │• Highest qual │
            └───────────────┘ └───────────────┘ └───────────────┘
                    │                 │                 │
                    └────────┬────────┴─────────────────┘
                             │
                             ▼
                    Provider Selection Strategy
                    ─────────────────────────────
                    Mode: "auto" (default)
                    1. Try LM Studio (if configured)
                    2. Try OpenAI (if API key set)
                    3. Fallback to Local

                    Mode: "local" | "openai" | "lmstudio"
                    Direct provider selection
```

### AI Decision Points

| Feature | Module | AI Involvement | Fallback |
|---------|--------|----------------|----------|
| Category Suggestion | `ai.py:analyze_transaction()` | Classify transaction | Local heuristics |
| Merchant Extraction | `ai.py:analyze_transaction()` | Extract merchant name | Regex patterns |
| Duplicate Detection | `ai_dedup.py` | Semantic similarity | Jaccard similarity |
| Category Matching | `ai_categories.py` | Fuzzy name matching | SequenceMatcher |
| Anomaly Detection | `realtime_anomaly_detection.py` | Pattern deviation | Statistical thresholds |

### Local AI Service (`ai.py:30-180`)

Pattern-based categorization without external API calls:

```python
CATEGORY_PATTERNS = {
    "Food & Dining": [
        r"restaurant", r"cafe", r"coffee", r"starbucks", r"mcdonald",
        r"pizza", r"burger", r"doordash", r"grubhub", r"uber\s*eats"
    ],
    "Transportation": [
        r"uber(?!\s*eats)", r"lyft", r"taxi", r"gas\s*station",
        r"shell", r"chevron", r"exxon", r"bp\s", r"parking"
    ],
    # ... more patterns
}

def suggest_categories(description: str, amount: float) -> List[CategorySuggestion]:
    # 1. Normalize description
    # 2. Match against patterns
    # 3. Consider amount thresholds
    # 4. Return sorted by confidence
```

### Confidence Escalation

```
┌─────────────────────────────────────────────────────────────────┐
│                    Confidence Threshold Flow                     │
└─────────────────────────────────────────────────────────────────┘

  Transaction ──► Local AI ──► Confidence ≥ 0.7? ──► YES ──► Accept
       │                              │
       │                              NO
       │                              │
       │                              ▼
       │                    LM Studio Available?
       │                              │
       │              YES ◄───────────┴───────────► NO
       │               │                             │
       │               ▼                             │
       │         Try LM Studio                       │
       │               │                             │
       │               ▼                             │
       │        Confidence ≥ 0.7?                    │
       │               │                             │
       │       YES ◄───┴───► NO                      │
       │        │             │                      │
       │        ▼             ▼                      │
       │     Accept    OpenAI Available? ◄──────────┘
       │                      │
       │          YES ◄───────┴───────► NO
       │           │                     │
       │           ▼                     ▼
       │      Try OpenAI           Mark as "needs_review"
       │           │
       │           ▼
       │    Accept (or "needs_review" if still low)
       │
       └──────────────────────────────────────────────────────────►
```

### Merchant Memory System

Learns from user categorization decisions:

```sql
-- When user categorizes a transaction:
INSERT INTO merchant_category_mapping
  (merchant_pattern, category_id, confidence, source, use_count)
VALUES
  ('STARBUCKS', 'uuid-food-dining', 0.95, 'user_correction', 1)
ON CONFLICT (merchant_pattern) DO UPDATE SET
  use_count = use_count + 1,
  last_used_at = NOW();
```

Future transactions from the same merchant auto-apply the learned category.

---

## 4. State Machines

### 4.1 Transaction Lifecycle

```
                                    ┌─────────────┐
                                    │   IMPORTED  │
                                    │  (Initial)  │
                                    └──────┬──────┘
                                           │
                      ┌────────────────────┼────────────────────┐
                      │                    │                    │
                      ▼                    ▼                    ▼
               ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
               │  DUPLICATE  │      │   PENDING   │      │  TRANSFER   │
               │  (Skipped)  │      │  (Analyze)  │      │ (Detected)  │
               └─────────────┘      └──────┬──────┘      └──────┬──────┘
                                           │                    │
                           ┌───────────────┼───────────────┐    │
                           │               │               │    │
                           ▼               ▼               ▼    │
                    ┌─────────────┐ ┌─────────────┐ ┌──────────┴──┐
                    │  RECURRING  │ │ CATEGORIZED │ │  CONFIRMED  │
                    │ (Detected)  │ │   (Auto)    │ │  TRANSFER   │
                    └──────┬──────┘ └──────┬──────┘ └─────────────┘
                           │               │
                           └───────┬───────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  REVIEWED   │
                            │  (Manual)   │
                            └─────────────┘
```

**State Transitions**:

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| - | IMPORTED | File upload | System |
| IMPORTED | DUPLICATE | Fingerprint match | System |
| IMPORTED | PENDING | Unique fingerprint | System |
| PENDING | CATEGORIZED | AI/Rule match | System |
| PENDING | TRANSFER | Transfer detection | System |
| PENDING | RECURRING | Pattern detection | System |
| TRANSFER | CONFIRMED_TRANSFER | User confirmation | User |
| CATEGORIZED | REVIEWED | User edit | User |
| * | REVIEWED | Manual categorization | User |

### 4.2 Transfer State Machine

```
┌─────────────────┐     detect_transfers()    ┌─────────────────┐
│    UNMATCHED    │──────────────────────────▶│    CANDIDATE    │
│                 │                           │  (confidence)   │
└─────────────────┘                           └────────┬────────┘
                                                       │
                                    ┌──────────────────┼──────────────────┐
                                    │                  │                  │
                                    ▼                  ▼                  ▼
                            ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
                            │   CONFIRMED   │  │   REJECTED    │  │   EXPIRED     │
                            │ (User Accept) │  │ (User Reject) │  │ (Timeout)     │
                            └───────────────┘  └───────────────┘  └───────────────┘

Database representation (match_transfer):
- decided_at IS NULL → CANDIDATE
- decided_at IS NOT NULL AND decided_by != 'rejected' → CONFIRMED
- decided_at IS NOT NULL AND decided_by = 'rejected' → REJECTED
```

### 4.3 Recurring Series State Machine

```
┌─────────────────┐     detect_recurring()     ┌─────────────────┐
│   UNDETECTED    │───────────────────────────▶│   CANDIDATE     │
│                 │                            │ (confidence<0.8)│
└─────────────────┘                            └────────┬────────┘
                                                        │
                              ┌──────────────────┬──────┴──────┬──────────────────┐
                              │                  │             │                  │
                              ▼                  ▼             ▼                  ▼
                      ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
                      │    ACTIVE     │  │   CONFIRMED   │  │   PAUSED      │  │  TERMINATED   │
                      │(conf >= 0.8)  │  │ (User Accept) │  │ (Missed 2+)   │  │ (User Delete) │
                      └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
                              │                                    │
                              │         new_occurrence()           │
                              └────────────────────────────────────┘

Database representation (recurring_series.is_active):
- is_active = true → ACTIVE
- is_active = false → PAUSED or TERMINATED
```

### 4.4 Import Run State Machine

```
┌─────────────────┐                           ┌─────────────────┐
│    CREATED      │──────────────────────────▶│   PROCESSING    │
│  (Run started)  │       File uploaded       │   (Parsing)     │
└─────────────────┘                           └────────┬────────┘
                                                       │
                                    ┌──────────────────┼──────────────────┐
                                    │                  │                  │
                                    ▼                  ▼                  ▼
                            ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
                            │   COMPLETED   │  │ PARTIAL_ERROR │  │    FAILED     │
                            │  (All good)   │  │ (Some failed) │  │  (All failed) │
                            └───────────────┘  └───────────────┘  └───────────────┘

Database representation (import_run):
- status = 'running' → PROCESSING
- status = 'completed' → COMPLETED
- status = 'partial' → PARTIAL_ERROR
- status = 'failed' → FAILED
```

---

## 5. Integration Points

### 5.1 System Integration Map

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                EXTERNAL SYSTEMS                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │   Bank PDFs     │       │   LM Studio     │       │     OpenAI      │
    │  (File Upload)  │       │ (localhost:1234)│       │   (API Cloud)   │
    └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
             │                         │                         │
             │ HTTP POST               │ HTTP POST               │ HTTP POST
             │ multipart/form-data     │ /v1/chat/completions    │ /v1/chat/completions
             │                         │                         │
             ▼                         ▼                         ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                              LEDGERLOOP BACKEND                                  │
    │                                                                                  │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
    │  │   Import    │  │  AI Service │  │  Analytics  │  │   Export    │             │
    │  │   Routes    │  │             │  │   Engine    │  │   Routes    │             │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘             │
    │                                                                                  │
    │                         ┌─────────────────────┐                                  │
    │                         │       DuckDB        │                                  │
    │                         │  (Thread-local)     │                                  │
    │                         └─────────────────────┘                                  │
    └─────────────────────────────────────────────────────────────────────────────────┘
             │
             │ HTTP REST API
             │ JSON responses
             ▼
    ┌─────────────────┐
    │   Next.js Web   │
    │    Frontend     │
    │  (localhost:3000)│
    └─────────────────┘
```

### 5.2 API Contract Summary

**Import Endpoints**:
```
POST /imports/upload
  Body: multipart/form-data {file, account_id}
  Response: {run_id, file_id, inserted, deduped, raw}

GET /imports/runs
  Response: [{id, started_at, source, status, file_count}]

DELETE /imports/runs/{run_id}
  Response: {deleted_transactions, deleted_files}
```

**Transaction Endpoints**:
```
GET /transactions
  Query: ?from=date&to=date&category_id=uuid&limit=100&offset=0
  Response: {items: [...], total, page}

PATCH /transactions/{id}
  Body: {category_id?, is_business?, is_income?}
  Response: {updated: true}

DELETE /transactions/{id}
  Response: {deleted: true}
```

**Analytics Endpoints**:
```
GET /analytics/summary
  Query: ?from=date&to=date&account_id=uuid
  Response: {totals, byMonth, byCategory, topMerchants}

GET /analytics/predictions
  Response: {budgetRisk, savingsOps, recurringForecast}
```

### 5.3 Database Connection Pattern

```python
# db.py - Thread-local connection pattern

import threading
_THREAD_LOCAL = threading.local()

def get_conn():
    """Get thread-local DuckDB connection"""
    if not hasattr(_THREAD_LOCAL, 'conn') or _THREAD_LOCAL.conn is None:
        _THREAD_LOCAL.conn = duckdb.connect(DB_PATH)
        _apply_schema(_THREAD_LOCAL.conn)
    return _THREAD_LOCAL.conn

# Self-healing on schema corruption:
def _apply_schema(conn):
    try:
        conn.execute(SCHEMA_SQL)
    except Exception as e:
        if "invalidated" in str(e):
            # Reconnect and retry once
            _THREAD_LOCAL.conn = duckdb.connect(DB_PATH)
            _THREAD_LOCAL.conn.execute(SCHEMA_SQL)
        else:
            raise
```

---

## 6. Configuration & Settings

### 6.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LEDGERLOOP_DB_PATH` | `~/.ledgerloop/ledgerloop.db` | Database file path |
| `LEDGERLOOP_AI_PROVIDER` | `local` | AI provider: local, openai, lmstudio, auto |
| `OPENAI_API_KEY` | - | OpenAI API key (if using openai provider) |
| `LEDGERLOOP_LM_STUDIO_URL` | `http://localhost:1234` | LM Studio endpoint |
| `LEDGERLOOP_AI_CONFIDENCE_THRESHOLD` | `0.7` | Min confidence for auto-accept |
| `LEDGERLOOP_UI_V1_COMPLETE` | `false` | Enable V1 UI features |

### 6.2 Runtime Settings (`settings.py`)

```python
DEFAULTS = {
    # AI Settings
    "ai_provider": "local",
    "ai_auto_categorize_min_conf": 0.7,
    "ai_model": "gpt-3.5-turbo",

    # Deduplication
    "dedup_days_window": 30,
    "dedup_min_confidence": 0.7,

    # Transfer Detection
    "transfer_time_window_days": 7,
    "transfer_amount_tolerance": 0.01,

    # Recurring Detection
    "recurring_min_occurrences": 3,
    "recurring_interval_tolerance": 0.15,

    # Analytics
    "analytics_cache_ttl_seconds": 120,

    # Business Rules
    "auto_categorize_on_import": True,
    "detect_transfers_on_import": True,
    "detect_recurring_on_import": False,
}
```

**Settings API**:
```
GET /settings
Response: {key: value, ...}

PUT /settings
Body: {key: value, ...}
Response: {updated: true}
```

### 6.3 Feature Flags

Stored in database `settings` table:

| Key | Type | Description |
|-----|------|-------------|
| `feature_ai_categorization` | bool | Enable AI categorization |
| `feature_transfer_detection` | bool | Enable transfer detection |
| `feature_recurring_detection` | bool | Enable recurring detection |
| `feature_merchant_memory` | bool | Learn from user corrections |
| `feature_realtime_analytics` | bool | Enable real-time updates |

---

## 7. Audit & Lineage

### 7.1 Event Log Schema

Every significant action is recorded in `event_log`:

```sql
CREATE TABLE event_log (
    id VARCHAR PRIMARY KEY,
    entity_type VARCHAR NOT NULL,  -- 'transaction', 'category', 'import', 'export', etc.
    entity_id VARCHAR NOT NULL,    -- ID of affected entity
    action VARCHAR NOT NULL,       -- 'create', 'update', 'delete', 'categorize', etc.
    payload_json TEXT,             -- JSON details of the change
    ts TIMESTAMP NOT NULL,         -- When it happened
    actor VARCHAR NOT NULL         -- 'user', 'ai_system', 'rule_engine', etc.
);
```

### 7.2 Tracked Actions

| Entity Type | Actions | Payload Contents |
|-------------|---------|------------------|
| `transaction` | create, update, delete, categorize, merge | old_value, new_value, reason |
| `category` | create, update, delete, auto_create | name, parent_id, confidence |
| `import` | start, complete, fail | file_count, record_count, errors |
| `export` | export:csv, export:parquet | filters, row_count |
| `transfer` | detect, confirm, reject | tx_ids, confidence, method |
| `recurring` | detect, confirm, pause, terminate | series_id, cadence, confidence |
| `rule` | create, update, delete, apply | predicate, action, match_count |
| `settings` | update | key, old_value, new_value |

### 7.3 Transaction Lineage

Complete provenance tracking from source to categorization:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              TRANSACTION LINEAGE                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

Source File                    Import Run                    Transaction
───────────────────────────────────────────────────────────────────────────────────────
import_file                    import_run                    transaction
├─ id: "file-uuid"             ├─ id: "run-uuid"             ├─ id: "tx-uuid"
├─ path: "boa_2025.pdf"        ├─ started_at: 2025-01-15     ├─ fingerprint: "sha1..."
├─ hash: "sha256..."           ├─ source: "upload:pdf"       ├─ source_raw_id: null
└─ type: "pdf"                 └─ status: "completed"        └─ created_at: 2025-01-15
       │                              │                              │
       │                              │                              │
       └──────────────────────────────┴──────────────────────────────┘
                                      │
                              transaction_ingest
                              ├─ tx_id: "tx-uuid"
                              ├─ run_id: "run-uuid"
                              └─ file_id: "file-uuid"


Categorization Chain
───────────────────────────────────────────────────────────────────────────────────────
transaction_category           event_log
├─ tx_id: "tx-uuid"            ├─ entity_type: "transaction"
├─ category_id: "cat-uuid"     ├─ entity_id: "tx-uuid"
├─ applied_by: "rule:uuid"     ├─ action: "categorize"
├─ confidence: 0.95            ├─ payload_json: {"category": "Food", "method": "rule"}
└─ applied_at: 2025-01-15      └─ actor: "rule_engine"
```

### 7.4 Query Examples

**Find all changes to a transaction**:
```sql
SELECT action, payload_json, ts, actor
FROM event_log
WHERE entity_type = 'transaction' AND entity_id = ?
ORDER BY ts DESC;
```

**Find source file for a transaction**:
```sql
SELECT f.path, f.hash, r.started_at, r.source
FROM transaction t
JOIN transaction_ingest ti ON t.id = ti.tx_id
JOIN import_file f ON ti.file_id = f.id
JOIN import_run r ON ti.run_id = r.id
WHERE t.id = ?;
```

**Audit trail for categorization**:
```sql
SELECT
    e.ts,
    e.actor,
    json_extract(e.payload_json, '$.category') as category,
    json_extract(e.payload_json, '$.method') as method,
    json_extract(e.payload_json, '$.confidence') as confidence
FROM event_log e
WHERE e.entity_type = 'transaction'
  AND e.entity_id = ?
  AND e.action = 'categorize'
ORDER BY e.ts DESC;
```

---

## Appendix A: File Reference

| File | Layer | Purpose |
|------|-------|---------|
| `db.py` | Storage | Database connection, schema management |
| `ingest_pdf.py` | Ingestion | PDF parsing and import |
| `normalization.py` | Ingestion | Text normalization |
| `dedup.py` | Ingestion | Fingerprint generation |
| `rules.py` | Classification | Rule engine |
| `ai.py` | Classification | AI service coordination |
| `ai_categories.py` | Classification | Smart category matching |
| `ai_dedup.py` | Detection | AI duplicate detection |
| `transfers.py` | Detection | Transfer detection |
| `recurring.py` | Detection | Recurring detection |
| `analytics.py` | Analytics | Aggregations, caching |
| `settings.py` | Configuration | Runtime settings |
| `api/*.py` | Presentation | REST API routes |

---

## Appendix B: Database Migrations

Schema versioning tracked in `schema_version` table:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL,
    description VARCHAR
);
```

Migration files in `db/migrations/`:
- `001_add_zelle_columns.sql`
- `002_add_merchant_memory.sql`
- `003_add_ai_tables.sql`
- etc.

Applied automatically on startup via `_run_migrations()`.

---

*Document generated: 2025-12-15*
*LedgerLoop Architecture v1.0*
