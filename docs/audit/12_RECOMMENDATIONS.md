# Recommendations

## Priority Matrix

| Priority | Timeline | Focus Area |
|----------|----------|------------|
| P0 - Critical | Immediate | Security vulnerabilities |
| P1 - High | This week | Performance, stability |
| P2 - Medium | This month | Code quality, testing |
| P3 - Low | Backlog | Refactoring, enhancements |

---

## P0 - Critical Fixes (Immediate)

### 1. Secure JWT Secret Generation

**Issue:** Default JWT secret is predictable

**Action:**
```python
# On first run, generate and store secure secret
import secrets

def get_or_create_jwt_secret():
    secret_file = data_dir() / ".jwt_secret"
    if secret_file.exists():
        return secret_file.read_text().strip()

    secret = secrets.token_urlsafe(32)
    secret_file.write_text(secret)
    return secret
```

**Effort:** 1 hour

### 2. Restrict CORS Origins

**Issue:** CORS allows all origins

**Action:**
```python
# api/__init__.py
allowed_origins = os.getenv("LEDGERLOOP_CORS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Effort:** 30 minutes

### 3. Add Production Mode Check

**Issue:** Admin endpoints unprotected

**Action:**
```python
# Add to admin routes
@router.on_event("startup")
async def check_security():
    if os.getenv("LEDGERLOOP_ENV") == "production":
        if os.getenv("LEDGERLOOP_JWT_SECRET") == "ledgerloop-dev-secret-change-in-production":
            raise RuntimeError("Production requires unique JWT secret")
```

**Effort:** 30 minutes

---

## P1 - High Priority (This Week)

### 4. Add Missing Database Indexes

**Issue:** Slow queries on common patterns

**Action:**
```sql
-- apps/backend/db/migrations/0006_performance_indexes.sql
CREATE INDEX IF NOT EXISTS idx_tx_ai_processed ON [transaction](ai_processed_at);
CREATE INDEX IF NOT EXISTS idx_tx_is_business ON [transaction](is_business);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transaction_category(category_id);
CREATE INDEX IF NOT EXISTS idx_mcm_merchant ON merchant_category_mapping(merchant_name);
```

**Effort:** 1 hour

### 5. Fix N+1 Query Patterns

**Issue:** Category fetched per transaction

**Action:**
```python
# Before
for tx in transactions:
    tx.category_name = get_category_name(tx.category_id)

# After
category_ids = {tx.category_id for tx in transactions if tx.category_id}
categories = {c.id: c.name for c in get_categories_by_ids(category_ids)}
for tx in transactions:
    tx.category_name = categories.get(tx.category_id)
```

**Effort:** 2 hours per module

### 6. Add Rate Limiting to AI Endpoints

**Issue:** Unbounded AI API costs

**Action:**
```python
# routes/ai.py
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/analyze/bulk")
@limiter.limit("10/minute")
async def analyze_bulk(request: Request, ...):
    ...
```

**Effort:** 1 hour

### 7. Standardize Error Responses

**Issue:** Inconsistent error formats

**Action:**
```python
# api/errors.py
class APIError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request.state.request_id
        }
    )
```

**Effort:** 4 hours

---

## P2 - Medium Priority (This Month)

### 8. Consolidate AI Modules

**Issue:** 19 AI modules with overlap

**Target Structure:**
```
ai/
├── __init__.py          # Public API
├── core.py              # AIService, providers
├── categorization.py    # All categorization logic
├── detection.py         # Transfer, P2P, recurring detection
├── quality.py           # Data quality, dedup
├── workflows.py         # Pipeline orchestration
└── prompts.py           # All prompt templates
```

**Effort:** 2-3 days

### 9. Improve Test Coverage

**Issue:** 45% coverage, AI modules excluded

**Action:**
1. Add unit tests for AI fallback behavior
2. Add integration tests for full import workflow
3. Add tests for edge cases in detection
4. Enable AI module coverage reporting

**Target:** 70% coverage

**Effort:** 1 week

### 10. Add Query Result Caching

**Issue:** Analytics recalculated on every request

**Action:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class AnalyticsCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache = {}

    def get_or_compute(self, key: str, compute_fn):
        now = datetime.utcnow()
        if key in self._cache:
            value, expires = self._cache[key]
            if now < expires:
                return value

        value = compute_fn()
        self._cache[key] = (value, now + timedelta(seconds=self.ttl))
        return value
```

**Effort:** 4 hours

### 11. Add Missing Type Hints

**Issue:** ~30% of functions lack type hints

**Action:**
```bash
# Install mypy
pip install mypy

# Run type checking
mypy apps/backend/src/ledgerloop --strict

# Fix incrementally
```

**Effort:** 2 days

### 12. Standardize API Response Formats

**Issue:** Inconsistent pagination

**Action:**
```python
# Standard response model
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    offset: int
    limit: int
    has_more: bool

# Use everywhere
@router.get("/transactions")
def list_transactions(...) -> PaginatedResponse[Transaction]:
    ...
```

**Effort:** 4 hours

---

## P3 - Low Priority (Backlog)

### 13. Remove Unused Dependencies

**Issue:** Zustand installed but unused

**Action:**
```bash
cd apps/web
npm uninstall zustand
```

**Effort:** 15 minutes

### 14. Add Docstrings

**Issue:** Many functions lack documentation

**Template:**
```python
def detect_recurring_candidates(
    conn: Connection,
    min_occurrences: int = 3,
    tolerance_days: int = 7
) -> List[RecurringCandidate]:
    """
    Detect potential recurring transaction series.

    Analyzes transaction history to identify patterns that suggest
    recurring payments (subscriptions, bills, etc.).

    Args:
        conn: Database connection
        min_occurrences: Minimum number of transactions to form a series
        tolerance_days: Allowed variance in payment dates

    Returns:
        List of candidate recurring series with confidence scores

    Example:
        >>> candidates = detect_recurring_candidates(conn, min_occurrences=3)
        >>> for c in candidates:
        ...     print(f"{c.name}: {c.cadence} (confidence: {c.confidence})")
    """
```

**Effort:** 3 days

### 15. Migrate to Modern Python Type Syntax

**Issue:** Using deprecated typing imports

**Before:**
```python
from typing import Optional, List, Dict
def foo(items: List[Dict[str, str]]) -> Optional[str]:
```

**After:**
```python
def foo(items: list[dict[str, str]]) -> str | None:
```

**Effort:** 2 hours

### 16. Remove Commented Code

**Action:**
```bash
# Find commented code
grep -rn "^#.*def \|^#.*class " apps/backend/src/

# Review and remove if not needed
```

**Effort:** 1 hour

### 17. Add OpenAPI Examples

**Issue:** No request/response examples in docs

**Action:**
```python
@router.post(
    "/transactions/{tx_id}/category",
    summary="Assign category to transaction",
    response_model=Transaction,
    responses={
        200: {
            "description": "Category assigned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "tx_123",
                        "category_id": "cat_456",
                        "category_name": "Food & Dining"
                    }
                }
            }
        }
    }
)
```

**Effort:** 4 hours

---

## Architecture Recommendations

### 1. Consider Message Queue for AI Jobs

**Current:** In-memory processing, background tasks
**Proposed:** Redis/Celery for job queue

**Benefits:**
- Survives restarts
- Better monitoring
- Scalable workers

**Effort:** 2-3 days

### 2. Add Read Replica Support

**Current:** Single SQLite writer
**Proposed:** Litestream for replication

**Benefits:**
- Read scaling
- Backup streaming
- Point-in-time recovery

**Effort:** 1 day

### 3. Implement Event Sourcing for Analytics

**Current:** Aggregate on demand
**Proposed:** Pre-computed materialized views

**Benefits:**
- Instant dashboard loads
- Historical analysis
- Audit trail

**Effort:** 1 week

### 4. Add Feature Flags

**Current:** Hard-coded feature toggles
**Proposed:** Runtime feature flags

**Benefits:**
- A/B testing
- Gradual rollouts
- Quick disable

**Effort:** 2 days

---

## Implementation Order

### Week 1
1. JWT secret generation (P0)
2. CORS restriction (P0)
3. Production mode check (P0)
4. Database indexes (P1)

### Week 2
5. N+1 query fixes (P1)
6. Rate limiting (P1)
7. Error standardization (P1)

### Week 3-4
8. AI module consolidation (P2)
9. Test coverage (P2)

### Month 2
10. Query caching (P2)
11. Type hints (P2)
12. Response standardization (P2)

### Ongoing
13-17. Low priority items as time permits

---

## Success Metrics

| Metric | Current | Target | Timeframe |
|--------|---------|--------|-----------|
| Security vulnerabilities | 3 | 0 | Week 1 |
| Average API response time | ~200ms | <100ms | Month 1 |
| Test coverage | 45% | 70% | Month 1 |
| Documented functions | 50% | 90% | Month 2 |
| Type-hinted functions | 70% | 95% | Month 2 |

---

*Generated by Claude Code Audit - December 27, 2025*
