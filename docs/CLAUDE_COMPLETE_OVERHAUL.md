# KASHAT COMPLETE OVERHAUL PROMPT
## For Claude Code CLI

---

## CONTEXT

You are taking over a personal finance application called **Kashat** (formerly LedgerLoop/Flos). 

**Location**: `C:\Users\Marwan\Desktop\AI\Flos`

This is a **local-first, privacy-focused** personal finance app with:
- FastAPI backend (Python 3.12)
- Next.js 14 frontend (React 18, TypeScript)
- SQLite database (WAL mode)
- 19 AI modules for categorization/detection
- 150+ API endpoints
- Statement import (CSV/PDF) - NO bank API integration

**Vision**: This app is part of a larger Life Management System (LMS) ecosystem. It must be clean, efficient, and production-ready. NOT an MVP - think long-term maintainability.

---

## CRITICAL CONSTRAINTS

### DO NOT:
- ❌ Add any authentication/authorization system
- ❌ Build agent/chat layer (that's Phase 2)
- ❌ Change the core import pipeline logic (it works)
- ❌ Remove any existing API endpoints
- ❌ Change database schema in breaking ways
- ❌ Delete user data or test with production data

### MUST:
- ✅ Maintain backward compatibility for all APIs
- ✅ Run tests after each major change
- ✅ Keep the app functional throughout refactoring
- ✅ Use incremental commits with clear messages
- ✅ Document all significant changes

---

## PHASE 1: RENAME TO KASHAT (2 hours)

### Files to Update:

```
apps/backend/pyproject.toml → name = "kashat"
apps/web/package.json → "name": "kashat-web"
docker-compose.yml → service names
README.md → all references
docs/*.md → all documentation
apps/web/src/app/layout.tsx → title, metadata
apps/web/public/manifest.json → app name (if exists)
Any .env.example files → KASHAT_* prefix
```

### Search and Replace:
```
"LedgerLoop" → "Kashat"
"ledgerloop" → "kashat"
"LEDGERLOOP_" → "KASHAT_"
"Flos" → "Kashat" (in user-facing text only)
```

### Branding to Apply:
```
Name: Kashat
Tagline: "Your money, your data, your rules."
Arabic: كاشاتك، بياناتك، قواعدك
```

### Validation:
- [ ] `npm run build` passes
- [ ] `pytest` passes
- [ ] App starts and loads dashboard
- [ ] No "LedgerLoop" visible in UI

---

## PHASE 2: PERFORMANCE FIXES (4 hours)

### 2.1 Database Indexes

**Read first**: `apps/backend/src/kashat/db.py`

**Create migration**: `apps/backend/db/migrations/0007_performance_indexes.sql`

```sql
-- Performance indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_tx_ai_processed ON [transaction](ai_processed_at);
CREATE INDEX IF NOT EXISTS idx_tx_is_business ON [transaction](is_business);
CREATE INDEX IF NOT EXISTS idx_tx_is_income ON [transaction](is_income);
CREATE INDEX IF NOT EXISTS idx_tx_posted_month ON [transaction](substr(posted_at, 1, 7));
CREATE INDEX IF NOT EXISTS idx_txcat_category ON transaction_category(category_id);
CREATE INDEX IF NOT EXISTS idx_mcm_merchant ON merchant_category_mapping(merchant_name);
CREATE INDEX IF NOT EXISTS idx_mcm_normalized ON merchant_category_mapping(normalized_pattern);
CREATE INDEX IF NOT EXISTS idx_recurring_next ON recurring_series(next_date);
CREATE INDEX IF NOT EXISTS idx_recurring_status ON recurring_series(status);
CREATE INDEX IF NOT EXISTS idx_p2p_counterparty ON p2p_transaction(counterparty_normalized);
CREATE INDEX IF NOT EXISTS idx_import_run_date ON import_run(started_at);
```

**Update db.py** to run this migration on startup.

### 2.2 Fix N+1 Query Patterns

**Files to fix**:
- `routes/transactions.py` - category name lookup
- `routes/recurring.py` - transaction count lookup
- `routes/analytics.py` - category aggregation

**Pattern to fix**:
```python
# BAD - N+1
for tx in transactions:
    tx.category_name = get_category_name(tx.category_id)

# GOOD - Batch
category_ids = list({tx.category_id for tx in transactions if tx.category_id})
if category_ids:
    categories = {c.id: c.name for c in get_categories_by_ids(conn, category_ids)}
    for tx in transactions:
        tx.category_name = categories.get(tx.category_id)
```

Search for these patterns across all route files and fix them.

### 2.3 Add Rate Limiting to AI Endpoints

**Install**: Add `slowapi` to requirements.txt

**Add to**: `routes/ai.py`, any endpoint calling external AI APIs

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/categorize")
@limiter.limit("30/minute")
async def categorize(...):
    ...

@router.post("/analyze/bulk")
@limiter.limit("10/minute")
async def analyze_bulk(...):
    ...
```

### 2.4 Add Query Result Caching

**Create**: `apps/backend/src/kashat/cache.py`

```python
from functools import lru_cache
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Any

T = TypeVar('T')

class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
    
    def get_or_compute(self, key: str, compute_fn: Callable[[], T]) -> T:
        now = datetime.utcnow()
        if key in self._cache:
            value, expires = self._cache[key]
            if now < expires:
                return value
        
        value = compute_fn()
        self._cache[key] = (value, now + timedelta(seconds=self.ttl))
        return value
    
    def invalidate(self, key: str = None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

# Global caches
analytics_cache = TTLCache(ttl_seconds=60)
category_cache = TTLCache(ttl_seconds=300)
```

**Apply to**: Analytics endpoints that compute aggregations.

### Validation:
- [ ] All tests pass
- [ ] Analytics endpoints respond faster (< 100ms)
- [ ] AI endpoints respect rate limits
- [ ] No database errors in logs

---

## PHASE 3: AI MODULE CONSOLIDATION (1 day)

### Current State (19 modules - TOO MANY):

```
ai.py (1497 lines) - Core service
ai_alerts.py
ai_analytics.py
ai_auto_categorization.py
ai_categories.py
ai_category_acceptance.py
ai_category_schemas.py
ai_data_quality.py
ai_dedup.py
ai_enhanced_categorization.py
ai_forecasting.py
ai_import.py
ai_insights.py
ai_integration.py
ai_intelligent_dedup.py
ai_smart_categorization.py
ai_transfer_detection.py
ai_workflow.py
ingest_ai_workflow.py
insights_ai_workflow.py
recurring_ai_workflow.py
merchant_intelligence.py
```

### Target State (6 modules):

```
ai/
├── __init__.py           # Public API exports
├── core.py               # AIService, AIConfig, providers
├── categorization.py     # ALL categorization (merge 5 files)
├── detection.py          # Transfer, P2P, recurring detection
├── quality.py            # Data quality, deduplication
├── workflows.py          # All pipeline orchestration
├── prompts.py            # All prompt templates (extract from files)
└── merchant.py           # Merchant intelligence (keep separate)
```

### Consolidation Rules:

**ai/core.py** - Take from:
- `ai.py`: AIService, AIConfig, provider logic, rate limiting
- `ai_integration.py`: Provider integration

**ai/categorization.py** - Merge:
- `ai_categories.py`
- `ai_enhanced_categorization.py`
- `ai_smart_categorization.py`
- `ai_auto_categorization.py`
- `ai_category_acceptance.py`
- `ai_category_schemas.py`

Keep ONE categorization pipeline:
1. Check merchant memory (learned patterns)
2. Check enhanced patterns (500+ regex patterns)
3. Fall back to AI with confidence thresholds

**ai/detection.py** - Merge:
- `ai_transfer_detection.py`
- Transfer logic from other files
- P2P detection logic
- Recurring detection AI parts

**ai/quality.py** - Merge:
- `ai_data_quality.py`
- `ai_dedup.py`
- `ai_intelligent_dedup.py`

**ai/workflows.py** - Merge:
- `ai_workflow.py`
- `ingest_ai_workflow.py`
- `insights_ai_workflow.py`
- `recurring_ai_workflow.py`
- `ai_import.py`

**ai/prompts.py** - Extract all prompts:
- Categorization prompt
- Merchant intelligence prompt
- Transfer analysis prompt
- PDF extraction prompt
- Quality analysis prompt

### Migration Steps:

1. Create `ai/` directory structure
2. Move code file by file, preserving functionality
3. Update ALL imports across codebase
4. Run tests after each file migration
5. Delete old files only after all tests pass
6. Update `__init__.py` exports for backward compatibility

### Backward Compatibility Layer:

```python
# ai/__init__.py
from .core import AIService, AIConfig
from .categorization import (
    categorize_transaction,
    get_category_suggestions,
    learn_merchant_pattern,
)
from .detection import (
    detect_transfers,
    detect_p2p,
    analyze_recurring,
)
from .quality import (
    calculate_quality_score,
    detect_duplicates,
)
from .workflows import (
    process_import_workflow,
    run_insights_workflow,
)
from .merchant import MerchantIntelligence

# Legacy aliases for backward compatibility
EnhancedCategorizer = categorize_transaction  # etc
```

### Validation:
- [ ] All 38 test files pass
- [ ] Import workflow still works end-to-end
- [ ] Categorization accuracy unchanged
- [ ] No import errors in any route file
- [ ] AI provider fallback still works

---

## PHASE 4: CODE QUALITY (4 hours)

### 4.1 Standardize Error Handling

**Create**: `apps/backend/src/kashat/errors.py`

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class KashatError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

class NotFoundError(KashatError):
    def __init__(self, resource: str, id: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found: {id}",
            status=404
        )

class ValidationError(KashatError):
    def __init__(self, field: str, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status=400,
            details={"field": field}
        )

class AIError(KashatError):
    def __init__(self, message: str, provider: str = None):
        super().__init__(
            code="AI_ERROR",
            message=message,
            status=503,
            details={"provider": provider}
        )

# Register handler in api/__init__.py
async def kashat_error_handler(request: Request, exc: KashatError):
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )
```

**Apply** these error classes across all route handlers.

### 4.2 Add Type Hints

Run through all Python files and add type hints:

```python
# Before
def get_transactions(conn, account_id=None, limit=100):
    ...

# After
def get_transactions(
    conn: Connection,
    account_id: str | None = None,
    limit: int = 100
) -> list[Transaction]:
    ...
```

Priority files:
- All route handlers
- All AI module functions
- All database functions

### 4.3 Add Docstrings

Use this format for all public functions:

```python
def detect_recurring_candidates(
    conn: Connection,
    min_occurrences: int = 3,
    tolerance_days: int = 7
) -> list[RecurringCandidate]:
    """
    Detect potential recurring transaction series.
    
    Analyzes transaction history to identify patterns suggesting
    recurring payments (subscriptions, bills, loans).
    
    Args:
        conn: Database connection
        min_occurrences: Minimum transactions to form a series
        tolerance_days: Allowed variance in payment dates
    
    Returns:
        List of candidate recurring series with confidence scores
    
    Example:
        >>> candidates = detect_recurring_candidates(conn)
        >>> for c in candidates:
        ...     print(f"{c.name}: {c.cadence}")
    """
```

### 4.4 Standardize API Responses

**Create**: `apps/backend/src/kashat/schemas/responses.py`

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool

class SuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict | None = None
```

**Apply** to all endpoints returning lists.

### 4.5 Remove Dead Code

Search and remove:
- Commented-out code blocks
- Unused imports (use `autoflake`)
- Unused functions (use `vulture`)
- Empty files

```bash
pip install autoflake vulture
autoflake --in-place --remove-all-unused-imports --recursive apps/backend/src/
vulture apps/backend/src/ --min-confidence 80
```

### 4.6 Fix Logging

Replace all `print()` statements with proper logging:

```python
import logging
logger = logging.getLogger(__name__)

# Replace
print(f"Processing {tx_id}")

# With
logger.info("Processing transaction", extra={"tx_id": tx_id})
```

### Validation:
- [ ] `mypy apps/backend/src/kashat --strict` passes (or minimal errors)
- [ ] No `print()` statements in production code
- [ ] All public functions have docstrings
- [ ] All tests pass

---

## PHASE 5: NEW FEATURES (1-2 days)

### 5.1 Net Worth View

**Database**: Add to schema
```sql
-- Add account_type to account table
ALTER TABLE account ADD COLUMN account_type TEXT DEFAULT 'checking';
-- Types: checking, savings, credit_card, loan, investment, asset

-- Add migration to update existing accounts
UPDATE account SET account_type = 
    CASE 
        WHEN lower(name) LIKE '%credit%' THEN 'credit_card'
        WHEN lower(name) LIKE '%saving%' THEN 'savings'
        WHEN lower(name) LIKE '%loan%' THEN 'loan'
        WHEN lower(name) LIKE '%mortgage%' THEN 'loan'
        ELSE 'checking'
    END;
```

**API**: `routes/networth.py`
```python
@router.get("/networth")
def get_net_worth(conn = Depends(get_conn)) -> NetWorthResponse:
    """Calculate net worth from all accounts."""
    accounts = get_all_accounts(conn)
    
    assets = sum(a.balance for a in accounts if a.account_type in ['checking', 'savings', 'investment', 'asset'])
    liabilities = sum(abs(a.balance) for a in accounts if a.account_type in ['credit_card', 'loan'])
    
    return NetWorthResponse(
        assets=assets,
        liabilities=liabilities,
        net_worth=assets - liabilities,
        by_type={...}
    )

@router.get("/networth/history")
def get_net_worth_history(...) -> list[NetWorthPoint]:
    """Get net worth over time (monthly snapshots)."""
```

**Frontend**: Create `apps/web/src/components/dashboard/NetWorthCard.tsx`

### 5.2 Bill Calendar

**API**: `routes/calendar.py`
```python
@router.get("/calendar/upcoming")
def get_upcoming_bills(
    days: int = 30,
    conn = Depends(get_conn)
) -> list[UpcomingBill]:
    """Get upcoming recurring payments for calendar view."""
    series = get_active_recurring_series(conn)
    upcoming = []
    
    for s in series:
        if s.next_date and parse_date(s.next_date) <= today + timedelta(days=days):
            upcoming.append(UpcomingBill(
                id=s.id,
                name=s.display_name or s.name,
                amount=s.amount_mean,
                due_date=s.next_date,
                recurring_type=s.recurring_type,
                is_essential=s.is_essential,
            ))
    
    return sorted(upcoming, key=lambda x: x.due_date)

@router.get("/calendar/month/{year}/{month}")
def get_month_calendar(...) -> MonthCalendar:
    """Get all bills for a specific month."""
```

**Frontend**: Create `apps/web/src/app/calendar/page.tsx` with calendar component

### 5.3 Smart Insight Cards

**API**: `routes/insights.py` (enhance existing)
```python
@router.get("/insights/cards")
def get_insight_cards(conn = Depends(get_conn)) -> list[InsightCard]:
    """Generate smart insight cards for dashboard."""
    cards = []
    
    # Spending spike detection
    spikes = detect_spending_spikes(conn)
    for spike in spikes:
        cards.append(InsightCard(
            type="spending_spike",
            title=f"Spending up on {spike.category}",
            message=f"You spent ${spike.current:.0f} this month vs ${spike.average:.0f} average",
            severity="warning" if spike.percent_change > 50 else "info",
            action_url=f"/transactions?category={spike.category_id}"
        ))
    
    # Price increase detection
    increases = detect_price_increases(conn)
    for inc in increases:
        cards.append(InsightCard(
            type="price_increase",
            title=f"{inc.merchant} price increased",
            message=f"Went from ${inc.old_price:.2f} to ${inc.new_price:.2f}",
            severity="warning",
            action_url=f"/recurring/{inc.series_id}"
        ))
    
    # Unused subscription detection
    unused = detect_unused_subscriptions(conn)
    for sub in unused:
        cards.append(InsightCard(
            type="unused_subscription",
            title=f"No activity: {sub.name}",
            message=f"Last charge was {sub.days_ago} days ago",
            severity="info",
            action_url=f"/recurring/{sub.series_id}"
        ))
    
    # Top spending categories
    top = get_top_categories_this_month(conn)
    cards.append(InsightCard(
        type="top_spending",
        title="Top spending this month",
        message=", ".join(f"{c.name}: ${c.total:.0f}" for c in top[:3]),
        severity="info"
    ))
    
    return cards[:10]  # Limit to 10 cards
```

**Insight detection functions**:
```python
def detect_spending_spikes(conn, threshold: float = 0.3) -> list[SpendingSpike]:
    """Find categories where current month > 3-month average by threshold."""
    
def detect_price_increases(conn, threshold: float = 0.05) -> list[PriceIncrease]:
    """Find recurring series where recent amount > previous amount."""
    
def detect_unused_subscriptions(conn, days: int = 45) -> list[UnusedSubscription]:
    """Find monthly subscriptions with no charge in last N days."""
```

**Frontend**: Update `apps/web/src/components/dashboard/IntelligenceFeed.tsx` to use new cards

### 5.4 Budget System

**Database**: Create tables
```sql
CREATE TABLE budget (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    period TEXT NOT NULL DEFAULT 'monthly',  -- monthly, weekly, yearly
    start_date TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE budget_category (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    amount_limit REAL NOT NULL,
    rollover INTEGER DEFAULT 0,  -- Carry unused to next period
    FOREIGN KEY (budget_id) REFERENCES budget(id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

CREATE TABLE budget_period (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    FOREIGN KEY (budget_id) REFERENCES budget(id)
);

CREATE INDEX idx_budget_category ON budget_category(budget_id);
CREATE INDEX idx_budget_period ON budget_period(budget_id, period_start);
```

**API**: `routes/budgets.py`
```python
@router.get("/budgets")
def list_budgets(...) -> list[Budget]: ...

@router.post("/budgets")
def create_budget(budget: BudgetCreate, ...) -> Budget: ...

@router.get("/budgets/{budget_id}")
def get_budget(budget_id: str, ...) -> BudgetDetail: ...

@router.get("/budgets/{budget_id}/progress")
def get_budget_progress(budget_id: str, ...) -> BudgetProgress:
    """Get current period spending vs budget limits."""

@router.put("/budgets/{budget_id}/categories/{category_id}")
def set_category_limit(...) -> BudgetCategory: ...
```

**Frontend**: Create `apps/web/src/app/budget/page.tsx` with:
- Budget overview cards
- Category progress bars
- Period selector
- Edit limits modal

### 5.5 Transaction Review Flag

**Database**:
```sql
ALTER TABLE [transaction] ADD COLUMN reviewed_at TEXT;
ALTER TABLE [transaction] ADD COLUMN reviewed_by TEXT;
```

**API**: Add to transactions routes
```python
@router.post("/transactions/{tx_id}/review")
def mark_reviewed(tx_id: str, ...) -> Transaction:
    """Mark transaction as reviewed."""

@router.post("/transactions/bulk/review")
def bulk_mark_reviewed(tx_ids: list[str], ...) -> BulkResult:
    """Mark multiple transactions as reviewed."""

@router.get("/transactions/unreviewed")
def get_unreviewed(limit: int = 50, ...) -> list[Transaction]:
    """Get transactions needing review."""
```

**Frontend**: Add checkbox column to transaction table, bulk action button

### Validation:
- [ ] Net worth calculates correctly
- [ ] Calendar shows upcoming bills
- [ ] Insight cards appear on dashboard
- [ ] Budget progress tracks accurately
- [ ] Review flag persists

---

## PHASE 6: FRONTEND POLISH (4 hours)

### 6.1 Dashboard Redesign

Update `apps/web/src/app/page.tsx` to show:

```
┌─────────────────────────────────────────────────────────┐
│  [Net Worth Card]    [Cash Flow Card]   [Budget Card]   │
├─────────────────────────────────────────────────────────┤
│  [Smart Insights Feed - 3 cards]                        │
├─────────────────────────────────────────────────────────┤
│  [Upcoming Bills]              [Recent Transactions]    │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Add Bill Calendar Page

Create `apps/web/src/app/calendar/page.tsx`:
- Monthly calendar view
- Bills shown on due dates
- Click to see details
- Color by type (subscription, bill, loan)

### 6.3 Update Navigation

Add to sidebar:
- 📊 Dashboard (/)
- 💳 Transactions
- 📅 Calendar (NEW)
- 🔄 Recurring
- 💰 Budget (NEW)
- 📈 Analytics
- ⚙️ Settings

### 6.4 Remove Unused Zustand

```bash
cd apps/web
npm uninstall zustand
```

Remove any empty store files.

### 6.5 Update Meta Tags

```tsx
// apps/web/src/app/layout.tsx
export const metadata = {
  title: 'Kashat',
  description: 'Your money, your data, your rules.',
  // Add proper OG tags
};
```

### Validation:
- [ ] Dashboard loads all new widgets
- [ ] Calendar page works
- [ ] Navigation updated
- [ ] No console errors
- [ ] Responsive on mobile

---

## PHASE 7: TESTING (4 hours)

### 7.1 Add Missing Tests

**AI Module Tests**: `tests/test_ai_consolidated.py`
```python
def test_categorization_pipeline():
    """Test full categorization: memory → patterns → AI fallback."""

def test_ai_provider_fallback():
    """Test fallback chain: LMStudio → OpenAI → local."""

def test_merchant_memory_learning():
    """Test that corrections are learned."""
```

**Feature Tests**: 
- `tests/test_networth.py`
- `tests/test_calendar.py`
- `tests/test_budget.py`
- `tests/test_insights.py`

**Integration Tests**: `tests/test_integration.py`
```python
def test_full_import_workflow():
    """Upload CSV → categorize → detect recurring → verify."""

def test_budget_tracking():
    """Create budget → add transactions → check progress."""
```

### 7.2 Increase Coverage Target

Update `pytest.ini` or `pyproject.toml`:
```toml
[tool.coverage.run]
branch = true
source = ["kashat"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 70
```

### 7.3 Run Full Test Suite

```bash
cd apps/backend
pytest --cov=kashat --cov-report=html -v
```

### Validation:
- [ ] Coverage ≥ 70%
- [ ] All new features tested
- [ ] AI fallback tested
- [ ] Integration tests pass

---

## PHASE 8: DOCUMENTATION (2 hours)

### 8.1 Update README

```markdown
# Kashat

Your money, your data, your rules.

## Features

- 📥 Import bank statements (CSV, PDF)
- 🤖 AI-powered categorization
- 🔄 Recurring payment detection
- 💸 Transfer matching
- 📊 Analytics & insights
- 💰 Budget tracking
- 📅 Bill calendar
- 🔒 100% local - your data never leaves your computer

## Quick Start

...
```

### 8.2 Update API Documentation

Add OpenAPI descriptions and examples to all new endpoints.

### 8.3 Create CHANGELOG

```markdown
# Changelog

## [2.0.0] - 2025-12-27

### Added
- Net worth tracking
- Bill calendar
- Smart insight cards
- Budget system
- Transaction review workflow

### Changed
- Renamed from LedgerLoop to Kashat
- Consolidated AI modules (19 → 6)
- Improved API response consistency
- Added rate limiting to AI endpoints

### Fixed
- N+1 query patterns
- Missing database indexes
- Inconsistent error handling
```

### 8.4 Update Architecture Docs

Update `docs/ARCHITECTURE_DEEP_DIVE.md` with:
- New module structure
- New database tables
- New API endpoints
- Updated data flows

---

## EXECUTION ORDER

```
1. RENAME (2 hours)
   └── Validate: App starts, tests pass

2. PERFORMANCE (4 hours)
   └── Validate: Faster queries, rate limits work

3. AI CONSOLIDATION (8 hours)
   └── Validate: All tests pass, categorization works

4. CODE QUALITY (4 hours)
   └── Validate: Type checks pass, no print statements

5. NEW FEATURES (12 hours)
   ├── Net Worth (2 hours)
   ├── Calendar (2 hours)
   ├── Insights (3 hours)
   ├── Budget (4 hours)
   └── Review Flag (1 hour)
   └── Validate: Features work end-to-end

6. FRONTEND POLISH (4 hours)
   └── Validate: UI looks good, responsive

7. TESTING (4 hours)
   └── Validate: Coverage ≥ 70%

8. DOCUMENTATION (2 hours)
   └── Validate: README accurate, API docs complete
```

**Total Estimated Time: 40 hours (1 week focused work)**

---

## FINAL VALIDATION CHECKLIST

Before marking complete:

- [ ] App renamed to Kashat throughout
- [ ] All 150+ API endpoints still work
- [ ] All tests pass (≥70% coverage)
- [ ] AI categorization works (test with real CSV)
- [ ] Recurring detection works
- [ ] Transfer matching works
- [ ] Net worth displays correctly
- [ ] Calendar shows upcoming bills
- [ ] Insights appear on dashboard
- [ ] Budget tracks spending
- [ ] No console errors in frontend
- [ ] No errors in backend logs
- [ ] Documentation updated
- [ ] Git history is clean with meaningful commits

---

## SUCCESS CRITERIA

When done, Kashat should:

1. **Work reliably** - No crashes, no data loss
2. **Perform well** - API responses < 100ms
3. **Be maintainable** - 6 AI modules, not 19
4. **Be complete** - All competitor features we identified
5. **Be documented** - README, API docs, architecture
6. **Be tested** - 70%+ coverage
7. **Be clean** - No dead code, consistent patterns

---

*Execute this prompt with Claude Code CLI. Take it phase by phase. Test after each phase. Don't rush.*
