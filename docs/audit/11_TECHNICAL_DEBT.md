# Technical Debt Analysis

## Overview

This document identifies code smells, inconsistencies, security concerns, and performance issues in the LedgerLoop codebase.

---

## Critical Issues

### 1. JWT Secret Default Value

**Location:** `docker-compose.yml`, `.env.example`

**Issue:** Default JWT secret is hardcoded as "ledgerloop-dev-secret-change-in-production"

```yaml
LEDGERLOOP_JWT_SECRET=${LEDGERLOOP_JWT_SECRET:-ledgerloop-dev-secret-change-in-production}
```

**Risk:** HIGH - Anyone with access to source code can forge tokens

**Fix:** Require secret generation on first run or fail startup without valid secret

### 2. Authentication Disabled

**Location:** `api/__init__.py`, route handlers

**Issue:** Admin endpoints lack authentication in single-user mode

**Risk:** HIGH - Any network access can perform admin operations

**Fix:** Implement authentication or restrict to localhost only

### 3. Single Worker Limitation

**Location:** `Dockerfile.backend`, documentation

**Issue:** SQLite requires single-writer mode, limiting scalability

```dockerfile
CMD ["gunicorn", ... "--workers", "1", ...]
```

**Risk:** MEDIUM - Cannot scale horizontally

**Fix:** Document clearly; consider DuckDB for read replicas

---

## Code Smells

### 1. AI Module Proliferation

**Location:** `apps/backend/src/ledgerloop/ai_*.py` (19 files)

**Issue:** Too many AI modules with overlapping functionality

| Module | Overlap With |
|--------|--------------|
| ai_categories.py | ai_enhanced_categorization.py, ai_smart_categorization.py |
| ai_dedup.py | ai_intelligent_dedup.py |
| ai_workflow.py | ingest_ai_workflow.py, insights_ai_workflow.py |

**Risk:** LOW - Maintenance burden, inconsistent behavior

**Fix:** Consolidate into fewer, well-defined modules

### 2. Large Functions

**Location:** Various

| File | Function | Lines | Concern |
|------|----------|-------|---------|
| ai.py | AIService.analyze_transaction | 100+ | Too complex |
| db.py | _upgrade_schema | 200+ | Should be migrations |
| recurring.py | detect_recurring_candidates | 150+ | Too many responsibilities |

**Fix:** Extract helper functions, use strategy pattern

### 3. Magic Numbers

**Location:** Various

```python
# ai.py
confidence_threshold: float = 0.7  # Why 0.7?
max_retries: int = 2              # Why 2?
requests_per_minute: int = 60     # Why 60?

# recurring.py
MIN_OCCURRENCES = 3               # Why 3?
TOLERANCE_DAYS = 7                # Why 7?
```

**Fix:** Document rationale or make configurable

### 4. Inconsistent Error Handling

**Location:** Route handlers

**Issue:** Some routes return detailed errors, others generic messages

```python
# Good
raise HTTPException(status_code=400, detail="Category not found")

# Bad
raise HTTPException(status_code=500, detail="Error")
```

**Fix:** Standardize error responses across all routes

---

## Inconsistencies

### 1. Naming Conventions

| Pattern | Examples | Count |
|---------|----------|-------|
| snake_case | get_transactions, detect_recurring | Most |
| camelCase | getConn (alias) | Few |
| Mixed | ai_workflow.py exports both | Some |

**Fix:** Enforce snake_case for Python, camelCase for TypeScript

### 2. API Response Formats

**Issue:** Inconsistent response structures

```python
# Some endpoints
{"items": [...], "total": 100}

# Others
{"data": [...], "count": 100}

# Others
[...]  # Raw array
```

**Fix:** Standardize on `{"items": [], "total": int, "offset": int, "limit": int}`

### 3. Test Patterns

**Issue:** Mixed unittest.TestCase and pytest styles

```python
# Some tests
class TestTransfers(unittest.TestCase):
    def test_something(self):
        ...

# Others
def test_something(db_conn, sample_data):
    ...
```

**Fix:** Migrate all to pytest fixtures

### 4. Logging Patterns

**Issue:** Inconsistent logging usage

```python
# Some modules
logger = logging.getLogger(__name__)
logger.info("Processing...")

# Others
print("Processing...")  # Bad
```

**Fix:** Enforce logging for all modules

---

## Security Concerns

### 1. SQL Injection Risk (LOW)

**Location:** `rules.py`

**Issue:** Dynamic SQL construction in rule predicates

```python
def predicate_to_sql(predicate: dict) -> str:
    # Constructs SQL from user input
```

**Mitigation:** Uses parameterized queries for values, but structure is dynamic

**Fix:** Validate predicate structure strictly

### 2. Path Traversal (LOW)

**Location:** `admin.py` backup/restore

**Issue:** File path construction from user input

```python
backup_path = Path(tmp_dir) / filename
```

**Mitigation:** Validates filename format

**Fix:** Use UUID for backup names, not user-provided

### 3. API Key Exposure (LOW)

**Location:** `ai.py`

**Issue:** API keys in memory, potentially in logs

**Mitigation:** Keys not logged explicitly

**Fix:** Add key masking to logging handlers

### 4. CORS Too Permissive

**Location:** `api/__init__.py`

```python
allow_origins=["*"],  # Too permissive for production
```

**Fix:** Restrict to known frontend origins

---

## Performance Concerns

### 1. N+1 Query Patterns

**Location:** Various route handlers

**Issue:** Fetching related data in loops

```python
for tx in transactions:
    category = get_category(tx.category_id)  # N queries
```

**Fix:** Use JOINs or batch fetching

### 2. Missing Indexes

**Location:** `db.py` schema

**Issue:** Some frequently-queried columns lack indexes

| Table | Column | Query Pattern |
|-------|--------|---------------|
| transaction | ai_processed_at | Filter unprocessed |
| transaction | is_business | Filter business |
| merchant_category_mapping | merchant_name | Lookup |

**Fix:** Add indexes for common query patterns

### 3. Large Payload Responses

**Location:** `transactions.py`

**Issue:** Can return 1000+ transactions with all fields

```python
limit: int = Query(default=100, le=2000)
```

**Fix:** Add pagination controls, field selection

### 4. Synchronous AI Calls

**Location:** `ai.py`

**Issue:** Some AI calls block the event loop

```python
response = requests.post(...)  # Blocking
```

**Fix:** Use httpx async client consistently

### 5. No Query Result Caching

**Location:** `analytics.py`

**Issue:** Analytics queries recalculated on every request

**Fix:** Add Redis/memcache or in-memory caching with TTL

---

## Dead Code

### 1. Unused Zustand Store

**Location:** `apps/web/src/stores/`

**Issue:** Zustand installed but directory empty, no imports

**Fix:** Remove zustand from package.json or implement stores

### 2. Legacy Route Redirects

**Location:** `next.config.js`

**Issue:** Old routes still have redirects

```javascript
{ source: '/analyze', destination: '/ai', permanent: true },
```

**Fix:** Remove after confirming no external links

### 3. Commented Code

**Location:** Various

```python
# def old_implementation():
#     ...
```

**Fix:** Remove commented code, use git history

---

## Documentation Gaps

### 1. Missing Docstrings

**Location:** Many functions

**Affected:**
- Most AI module functions
- Many route handlers
- Helper functions

**Fix:** Add docstrings with parameter descriptions

### 2. Missing Type Hints

**Location:** Various

**Coverage:** ~70% estimated

**Fix:** Add type hints to all public functions

### 3. No API Documentation

**Location:** N/A

**Issue:** No Swagger UI customization, no examples

**Fix:** Add OpenAPI descriptions and examples

---

## Dependency Issues

### 1. DuckDB vs SQLite Confusion

**Location:** `db.py`, `requirements.txt`

**Issue:** DuckDB in requirements but SQLite used primarily

**Fix:** Clarify usage, remove if unused

### 2. Outdated Import Style

**Location:** Various

```python
from typing import Optional, List  # Deprecated in 3.10+
```

**Fix:** Use `list` and `| None` syntax

---

## Quantified Metrics

| Metric | Count | Target |
|--------|-------|--------|
| TODO/FIXME comments | ~20 | 0 |
| Functions > 50 lines | ~15 | 5 |
| Files > 500 lines | ~5 | 3 |
| Missing docstrings | ~50% | <10% |
| Missing type hints | ~30% | <5% |
| Test coverage | 45% | 70% |
| Duplicate code blocks | ~10 | 0 |

---

## Priority Matrix

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| JWT Secret Default | HIGH | LOW | P0 |
| Authentication Disabled | HIGH | MEDIUM | P0 |
| CORS Too Permissive | MEDIUM | LOW | P1 |
| AI Module Consolidation | LOW | HIGH | P2 |
| N+1 Queries | MEDIUM | MEDIUM | P1 |
| Missing Indexes | MEDIUM | LOW | P1 |
| Test Coverage | LOW | HIGH | P2 |
| Documentation | LOW | MEDIUM | P3 |

---

*Generated by Claude Code Audit - December 27, 2025*
