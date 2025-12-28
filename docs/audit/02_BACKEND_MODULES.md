# Backend Modules Documentation

## Module Categories

| Category | Count | Purpose |
|----------|-------|---------|
| Core | 7 | Configuration, database, logging |
| API | 23 | HTTP endpoints |
| Business Logic | 11 | Core features |
| AI/ML | 19 | Intelligence layer |
| Detection | 4 | Pattern detection |
| Parsing | 3 | File parsing |

---

## Core Modules

### config.py
**Purpose:** Application configuration and paths

```python
def data_dir() -> Path:
    """Get data directory, handles WSL and fallbacks."""

def db_path() -> Path:
    """Get database file path."""

def tmp_dir() -> Path:
    """Get temporary file directory."""
```

**Key Features:**
- WSL path detection
- Home directory writability check
- Environment variable overrides
- Pytest isolation support

### db.py (734 lines)
**Purpose:** SQLite connection management and schema

```python
class SQLiteConnectionWrapper:
    """Wrapper for DuckDB-compatible interface."""

def connect(path: Path = None) -> SQLiteConnectionWrapper:
    """Get or create thread-local connection."""

def get_conn() -> SQLiteConnectionWrapper:
    """Alias for connect()."""

def close() -> None:
    """Close thread-local connection."""
```

**Key Features:**
- Thread-local connections
- WAL mode for concurrency
- Automatic schema creation
- Migration system
- 25+ table definitions

### logging_config.py
**Purpose:** Centralized logging setup

```python
def setup_logging() -> None:
    """Configure logging with file rotation."""
```

### metrics.py
**Purpose:** Prometheus metrics

```python
# Counters and histograms for monitoring
REQUESTS_TOTAL = Counter('ledgerloop_requests_total', ...)
REQUEST_LATENCY = Histogram('ledgerloop_request_latency_seconds', ...)

def generate_latest() -> bytes:
    """Generate Prometheus metrics output."""
```

### security.py
**Purpose:** Security utilities

```python
def redact_sensitive(text: str) -> str:
    """Redact credit card numbers, tokens, etc."""
```

### settings.py
**Purpose:** Runtime settings management

```python
def get_settings(conn) -> dict:
    """Get all settings from database."""

def set_setting(conn, key: str, value: Any) -> None:
    """Update a setting."""
```

### cli.py (488 lines)
**Purpose:** Command-line interface

```python
@click.group()
def cli():
    """LedgerLoop CLI."""

@cli.command()
def ingest(file: Path):
    """Import CSV or PDF file."""

@cli.command()
def stats():
    """Show database statistics."""

@cli.command()
def classify():
    """Run AI classification."""
```

**Commands:**
- `ledgerloop ingest <file>` - Import file
- `ledgerloop stats` - Database statistics
- `ledgerloop classify` - AI categorization
- `ledgerloop detect transfers` - Transfer detection
- `ledgerloop detect recurring` - Recurring detection
- `ledgerloop export <format>` - Export data
- `ledgerloop health` - System health

---

## Business Logic Modules

### ingest_csv.py
**Purpose:** CSV file import

```python
def import_csv_upload(
    conn,
    file_content: bytes,
    account_id: str,
    run_id: str = None
) -> ImportResult:
    """Parse and import CSV file."""
```

**Process:**
1. Detect CSV format
2. Parse rows
3. Normalize descriptions
4. Generate fingerprints
5. Deduplicate
6. Insert transactions

### ingest_pdf.py
**Purpose:** PDF file import

```python
def import_pdf_upload(
    conn,
    file_content: bytes,
    account_id: str,
    run_id: str = None
) -> ImportResult:
    """Parse and import PDF bank statement."""
```

**Features:**
- Bank auto-detection
- Table extraction
- AI vision fallback
- Balance validation

### normalization.py
**Purpose:** Data normalization utilities

```python
def normalize_description(desc: str) -> str:
    """Clean and normalize transaction description."""

def parse_amount(row: dict) -> float:
    """Extract amount from various column formats."""

def parse_date(row: dict) -> str:
    """Parse date to ISO format."""

def normalize_currency(value: str) -> str:
    """Normalize currency code."""
```

### dedup.py
**Purpose:** Transaction deduplication

```python
def tx_fingerprint(
    account_id: str,
    posted_at: str,
    amount: float,
    description: str
) -> str:
    """Generate SHA1 fingerprint for deduplication."""
```

### recurring.py
**Purpose:** Recurring payment detection

```python
def detect_recurring_candidates(conn, min_occurrences: int = 3) -> List[dict]:
    """Identify potential recurring series."""

def suggest_recurring(conn, limit: int = 100) -> List[dict]:
    """Get pending recurring suggestions."""

def confirm_recurring(conn, series_id: str) -> None:
    """Confirm a recurring series."""

def reject_recurring(conn, series_id: str) -> None:
    """Reject a recurring series."""
```

**Detection Criteria:**
- Minimum 3 occurrences
- Consistent intervals
- Similar amounts
- Same merchant pattern

### recurring_classifier.py
**Purpose:** Cadence classification

```python
def detect_cadence(intervals: List[int]) -> str:
    """Determine cadence from intervals."""
    # Returns: weekly, biweekly, monthly, quarterly, yearly
```

### recurring_insights.py
**Purpose:** Recurring analytics

```python
def get_recurring_insights(conn) -> dict:
    """Calculate recurring spending insights."""
```

### transfers.py
**Purpose:** Transfer pair detection

```python
def suggest_transfers(
    conn,
    max_days: int = 3,
    amount_tolerance: float = 0.02
) -> List[dict]:
    """Find potential transfer pairs."""

def confirm_transfer(conn, left_id: str, right_id: str) -> None:
    """Confirm a transfer pair."""

def jaccard_similarity(a: str, b: str) -> float:
    """Calculate description similarity."""
```

### rules.py
**Purpose:** Rule engine

```python
class RulePredicate:
    """Rule condition (regex, amount, merchant)."""

class RuleAction:
    """Rule action (set category, add tag)."""

def apply_rule(conn, rule_id: str) -> int:
    """Apply rule to matching transactions."""

def apply_all_rules(conn) -> int:
    """Apply all enabled rules."""
```

### p2p_detection.py
**Purpose:** P2P payment detection

```python
def detect_p2p(description: str) -> Optional[P2PInfo]:
    """Detect Zelle, Venmo, CashApp, etc."""

def parse_zelle(description: str) -> Optional[dict]:
    """Parse Zelle payment details."""

def parse_venmo(description: str) -> Optional[dict]:
    """Parse Venmo payment details."""
```

### merchant_intelligence.py (697 lines)
**Purpose:** Merchant extraction and caching

```python
class MerchantIntelligence:
    """LLM-powered merchant analysis."""

    def analyze(self, description: str, amount: float) -> MerchantInfo:
        """Extract merchant info with caching."""

    def analyze_batch(self, items: List[tuple]) -> List[MerchantInfo]:
        """Batch analysis for efficiency."""
```

**Features:**
- 30-day response cache
- Hit tracking
- Multi-provider support
- Recurring type classification

---

## AI Modules

### ai.py (1,497 lines)
**Purpose:** Core AI service orchestration

```python
@dataclass
class AIConfig:
    """AI service configuration."""

class LocalAIService:
    """Pattern-based fallback."""

class OpenAIService:
    """OpenAI/LM Studio client."""

class AIService:
    """Main orchestrator with provider escalation."""

    def analyze_transaction(self, description: str, amount: float) -> dict:
        """Analyze single transaction."""

    def analyze_batch(self, transactions: List[dict]) -> List[dict]:
        """Batch analysis."""
```

### ai_workflow.py (510 lines)
**Purpose:** Pipeline orchestration

```python
class AIWorkflow:
    """End-to-end processing pipeline."""

    def process_import(self, run_id: str) -> WorkflowResult:
        """Process imported transactions."""
```

**Stages:**
1. Import extraction
2. AI enhancement
3. Rule application
4. Duplicate detection
5. Quality validation
6. Completion

### ai_auto_categorization.py (795 lines)
**Purpose:** Confidence-based auto-categorization

```python
class AutoCategorizationEngine:
    """Auto-apply categories with learning."""

    def process_transaction(self, tx_id: str) -> CategorizeResult:
        """Categorize single transaction."""

    def batch_process(self, tx_ids: List[str]) -> BatchResult:
        """Process multiple transactions."""

    def learn_from_correction(self, tx_id: str, category_id: str) -> None:
        """Learn from user correction."""
```

### Other AI Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| ai_categories.py | ~300 | Category matching |
| ai_enhanced_categorization.py | ~400 | Enhanced patterns |
| ai_smart_categorization.py | ~350 | ML-based matching |
| ai_category_acceptance.py | ~200 | User acceptance |
| ai_category_schemas.py | ~150 | Schema definitions |
| ai_import.py | ~400 | Import enhancement |
| ai_dedup.py | ~300 | Semantic dedup |
| ai_intelligent_dedup.py | ~250 | Advanced dedup |
| ai_data_quality.py | ~350 | Quality scoring |
| ai_transfer_detection.py | ~300 | AI transfer matching |
| ai_analytics.py | ~250 | Predictive analytics |
| ai_forecasting.py | ~300 | Cash flow forecasting |
| ai_insights.py | ~250 | Behavioral insights |
| ai_alerts.py | ~200 | Anomaly alerts |
| ai_integration.py | ~200 | Provider integration |
| ingest_ai_workflow.py | ~400 | Import workflow |
| insights_ai_workflow.py | ~300 | Insights workflow |
| recurring_ai_workflow.py | ~350 | Recurring workflow |

---

## Detection Modules

### detect/zelle.py
**Purpose:** Zelle transaction detection

```python
def detect_zelle(description: str) -> Optional[ZelleInfo]:
    """Parse Zelle payment details."""
```

### detect/p2p.py
**Purpose:** P2P descriptor parsing

```python
def parse_p2p_descriptor(description: str) -> Optional[P2PInfo]:
    """Parse any P2P payment (Venmo, CashApp, etc.)."""
```

### detect/income.py
**Purpose:** Income categorization

```python
def detect_income(transactions: List[dict]) -> List[str]:
    """Identify income transactions by pattern."""
```

### detect/adjustments.py
**Purpose:** Cashback/reversal detection

```python
def detect_adjustments(transactions: List[dict]) -> List[str]:
    """Identify adjustment transactions."""
```

---

## Parsing Modules

### parse/ai_parser.py
**Purpose:** AI-powered PDF parsing

```python
class AIParser:
    """PDF parsing with vision models."""

    def parse(self, pdf_bytes: bytes) -> List[dict]:
        """Extract transactions from PDF."""
```

**Providers:**
- OpenAI GPT-4o (native PDF)
- LM Studio (image conversion)

### parse/banks/boa_v2025.py
**Purpose:** Bank of America PDF parser

```python
def parse_boa_statement(pdf_bytes: bytes) -> ParseResult:
    """Parse BoA PDF statement."""
```

**Features:**
- Table extraction
- Balance validation
- Multi-page support
- Date normalization

---

## Analytics Modules

### analytics/predictive_engine.py
**Purpose:** Predictive modeling

```python
class PredictiveEngine:
    """Cash flow and spending predictions."""

    def forecast_cashflow(self, months: int = 3) -> CashflowForecast:
        """Project future cash flow."""

    def predict_category_spending(self, category: str) -> SpendingPrediction:
        """Predict category spending."""
```

---

## Module Dependencies Graph

```
config.py
    ↓
db.py ←─────────────────────────────────────────┐
    ↓                                            │
logging_config.py                                │
    ↓                                            │
api/__init__.py ← routes/*.py                    │
    ↓                                            │
business logic (recurring, transfers, rules) ────┘
    ↓
ai.py ← ai_*.py
    ↓
parse/*.py
```

---

*Generated by Claude Code Audit - December 27, 2025*
