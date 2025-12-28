# KASHAT NEW FEATURES & PIPELINE SEQUENCE VALIDATION
## For Claude Code CLI

---

## MISSION

You are validating:
1. **All 5 new features** work correctly with real data (2,118 transactions)
2. **Pipeline sequence** is correct and properly ordered
3. **Integration points** between features work

**Location**: `C:\Users\Marwan\Desktop\AI\Flos`
**Data**: Already imported (2,118 transactions, 61 recurring series, 160 P2P)

---

## PART A: PIPELINE SEQUENCE AUDIT

### A.1 Document Current Pipeline Order

**Find and read these files to understand current flow:**
```
apps/backend/src/kashat/
├── routes/import.py          # Where does import start?
├── ai/workflows.py           # What's the workflow order?
├── services/import_service.py # Import orchestration
├── services/ingest.py        # Ingestion logic
```

**Questions to answer:**
1. What happens when a file is uploaded?
2. In what order are these steps executed?
3. Are there dependencies between steps?
4. Can steps run in parallel or must be sequential?

### A.2 Expected Correct Pipeline Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                    KASHAT PIPELINE SEQUENCE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. IMPORT STAGE                                                 │
│     ├── File Upload (CSV/PDF)                                    │
│     ├── File Parsing (extract raw transactions)                  │
│     ├── Normalization (dates, amounts, descriptions)             │
│     └── Fingerprint Generation (unique ID per transaction)       │
│                                                                  │
│  2. DEDUPLICATION STAGE                                          │
│     ├── Check fingerprint against existing                       │
│     ├── Fuzzy matching for near-duplicates                       │
│     └── Mark/skip duplicates                                     │
│                                                                  │
│  3. CATEGORIZATION STAGE                                         │
│     ├── Check merchant memory (learned patterns)                 │
│     ├── Check rules engine (user-defined rules)                  │
│     ├── Check enhanced patterns (500+ regex)                     │
│     └── AI categorization (LLM fallback)                         │
│                                                                  │
│  4. TRANSFER DETECTION STAGE  ⚠️ MUST BE BEFORE RECURRING        │
│     ├── Find matching pairs (same amount, opposite sign)         │
│     ├── Apply similarity algorithms (V1, V2, V3)                 │
│     └── Mark as internal transfers                               │
│                                                                  │
│  5. P2P DETECTION STAGE                                          │
│     ├── Pattern matching (Zelle, Venmo, etc.)                    │
│     ├── Extract counterparty names                               │
│     └── Classify P2P type                                        │
│                                                                  │
│  6. RECURRING DETECTION STAGE  ⚠️ MUST BE AFTER TRANSFERS        │
│     ├── Group by merchant/description                            │
│     ├── Calculate intervals                                      │
│     ├── Detect cadence (monthly, weekly, etc.)                   │
│     └── Create recurring series                                  │
│                                                                  │
│  7. ENRICHMENT STAGE                                             │
│     ├── Business vs personal classification                      │
│     ├── Income detection                                         │
│     └── Merchant intelligence                                    │
│                                                                  │
│  8. QUALITY STAGE                                                │
│     ├── Data quality scoring                                     │
│     ├── Anomaly detection                                        │
│     └── Issue flagging                                           │
│                                                                  │
│  9. INSIGHTS STAGE (runs on-demand or scheduled)                 │
│     ├── Spending pattern analysis                                │
│     ├── Price change detection                                   │
│     ├── Unused subscription detection                            │
│     └── Generate insight cards                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### A.3 Verify Actual Implementation Matches

**Check each stage exists and is called in correct order:**

```python
# Create a test script to trace the pipeline
import logging
logging.basicConfig(level=logging.DEBUG)

# Trace what happens during import
# Add logging to each stage to verify order
```

**Document findings:**
```markdown
## PIPELINE_AUDIT.md

### Stage 1: Import
- File: [filename]
- Function: [function_name]
- Called by: [caller]
- Calls next: [next_stage]

### Stage 2: Deduplication
...
```

### A.4 Identify Pipeline Issues

**Check for these problems:**

| Issue | Check | Status |
|-------|-------|--------|
| Transfers detected AFTER recurring? | Could cause recurring to include transfers | ❓ |
| Categorization before dedup? | Could waste AI calls on duplicates | ❓ |
| P2P detection isolated? | Should inform recurring detection | ❓ |
| Insights run automatically? | Should be on-demand or scheduled | ❓ |
| Quality checks at end? | Should run after all enrichment | ❓ |

### A.5 Fix Pipeline Order If Needed

If pipeline order is wrong, create a fix:

```python
# apps/backend/src/kashat/services/pipeline_orchestrator.py

class PipelineOrchestrator:
    """Ensures correct execution order of all pipelines."""
    
    STAGE_ORDER = [
        'import',
        'deduplicate', 
        'categorize',
        'detect_transfers',  # BEFORE recurring!
        'detect_p2p',
        'detect_recurring',  # AFTER transfers!
        'enrich',
        'quality_check',
    ]
    
    async def run_full_pipeline(self, import_run_id: str):
        """Execute all stages in correct order."""
        for stage in self.STAGE_ORDER:
            logger.info(f"Starting stage: {stage}")
            await getattr(self, f"_run_{stage}")(import_run_id)
            logger.info(f"Completed stage: {stage}")
```

---

## PART B: NEW FEATURES TESTING

### B.1 Net Worth Feature

**API Endpoints to test:**
```bash
# Get net worth
curl http://localhost:8000/api/networth

# Get net worth history
curl http://localhost:8000/api/networth/history

# Check account types are set
curl http://localhost:8000/api/accounts
```

**Validation checklist:**
- [ ] Endpoint exists and returns data
- [ ] Account types are correctly identified (checking, credit, savings, loan)
- [ ] Assets sum correctly
- [ ] Liabilities sum correctly (as positive number)
- [ ] Net worth = assets - liabilities
- [ ] History shows monthly snapshots

**Test with real data:**
```python
import requests

# Get accounts
accounts = requests.get("http://localhost:8000/api/accounts").json()
print("Accounts:")
for a in accounts:
    print(f"  {a['name']}: ${a['balance']:.2f} ({a.get('account_type', 'unknown')})")

# Get net worth
nw = requests.get("http://localhost:8000/api/networth").json()
print(f"\nNet Worth Calculation:")
print(f"  Assets: ${nw.get('assets', 0):.2f}")
print(f"  Liabilities: ${nw.get('liabilities', 0):.2f}")
print(f"  Net Worth: ${nw.get('net_worth', 0):.2f}")

# Verify math
expected = nw.get('assets', 0) - nw.get('liabilities', 0)
actual = nw.get('net_worth', 0)
assert abs(expected - actual) < 0.01, f"Math error: {expected} != {actual}"
print("✅ Net worth calculation correct")
```

**If issues found, fix:**
- Missing endpoint → Create in routes/networth.py
- Wrong account types → Update migration/detection logic
- Math wrong → Fix calculation in service

---

### B.2 Bill Calendar Feature

**API Endpoints to test:**
```bash
# Get upcoming bills (next 30 days)
curl http://localhost:8000/api/calendar/upcoming

# Get specific month
curl http://localhost:8000/api/calendar/month/2025/01

# Get next bill dates
curl http://localhost:8000/api/recurring
```

**Validation checklist:**
- [ ] Endpoint exists and returns data
- [ ] Uses recurring_series.next_date
- [ ] Bills sorted by date
- [ ] Includes amount, name, type
- [ ] Handles missing next_date gracefully

**Test with real data:**
```python
import requests
from datetime import datetime, timedelta

# We have 61 recurring series - how many have next_date set?
recurring = requests.get("http://localhost:8000/api/recurring").json()
with_next_date = [r for r in recurring if r.get('next_date')]
print(f"Recurring series with next_date: {len(with_next_date)}/{len(recurring)}")

# Get upcoming bills
upcoming = requests.get("http://localhost:8000/api/calendar/upcoming?days=30").json()
print(f"\nUpcoming bills (next 30 days): {len(upcoming)}")

for bill in upcoming[:10]:
    print(f"  {bill.get('due_date')}: {bill.get('name')} - ${bill.get('amount', 0):.2f}")

# Verify bills are sorted
dates = [bill.get('due_date') for bill in upcoming]
assert dates == sorted(dates), "Bills not sorted by date!"
print("✅ Bills correctly sorted")
```

**If issues found:**
- No next_date → Recurring detection needs to calculate next occurrence
- Wrong dates → Check recurring_type cadence logic
- Missing endpoint → Create routes/calendar.py

---

### B.3 Budget System Feature

**API Endpoints to test:**
```bash
# List budgets
curl http://localhost:8000/api/budgets

# Create a test budget
curl -X POST http://localhost:8000/api/budgets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monthly Budget",
    "period": "monthly"
  }'

# Add category limits
curl -X POST http://localhost:8000/api/budgets/{budget_id}/categories \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "food",
    "amount_limit": 500
  }'

# Get budget progress
curl http://localhost:8000/api/budgets/{budget_id}/progress
```

**Validation checklist:**
- [ ] Can create budget
- [ ] Can set category limits
- [ ] Progress calculates spent vs limit
- [ ] Percentage calculation correct
- [ ] Over-budget detection works
- [ ] Period boundaries correct

**Test with real data:**
```python
import requests

# Create a budget
budget = requests.post(
    "http://localhost:8000/api/budgets",
    json={"name": "Test Budget", "period": "monthly"}
).json()
budget_id = budget.get('id')
print(f"Created budget: {budget_id}")

# Get categories to set limits
categories = requests.get("http://localhost:8000/api/categories").json()
print(f"Available categories: {len(categories)}")

# Set limit for top category
if categories:
    cat = categories[0]
    limit_response = requests.post(
        f"http://localhost:8000/api/budgets/{budget_id}/categories",
        json={"category_id": cat['id'], "amount_limit": 500}
    )
    print(f"Set limit for {cat['name']}: $500")

# Get progress
progress = requests.get(f"http://localhost:8000/api/budgets/{budget_id}/progress").json()
print(f"\nBudget Progress:")
for cat_progress in progress.get('categories', []):
    pct = cat_progress.get('percentage', 0)
    status = "🔴" if pct > 100 else "🟡" if pct > 80 else "🟢"
    print(f"  {status} {cat_progress['name']}: ${cat_progress['spent']:.2f} / ${cat_progress['limit']:.2f} ({pct:.0f}%)")

# Clean up test budget
requests.delete(f"http://localhost:8000/api/budgets/{budget_id}")
```

**If issues found:**
- Endpoint missing → Create routes/budgets.py
- Progress wrong → Fix spending aggregation query
- Period wrong → Check date boundary logic

---

### B.4 Smart Insight Cards Feature

**API Endpoints to test:**
```bash
# Get insight cards
curl http://localhost:8000/api/insights/cards

# Get specific insight types
curl http://localhost:8000/api/insights/spending-spikes
curl http://localhost:8000/api/insights/price-increases
curl http://localhost:8000/api/insights/unused-subscriptions
```

**Validation checklist:**
- [ ] Endpoint returns cards
- [ ] Spending spikes detected (compare to average)
- [ ] Price increases detected (recurring amount changes)
- [ ] Unused subscriptions detected (no recent charge)
- [ ] Cards have type, title, message, severity
- [ ] Action URLs are correct

**Test with real data:**
```python
import requests

# Get insight cards
cards = requests.get("http://localhost:8000/api/insights/cards").json()
print(f"Insight cards generated: {len(cards)}")

# Group by type
from collections import Counter
types = Counter(c.get('type') for c in cards)
print(f"\nCard types:")
for t, count in types.items():
    print(f"  {t}: {count}")

# Show sample cards
print(f"\nSample cards:")
for card in cards[:5]:
    severity_icon = {"warning": "⚠️", "info": "ℹ️", "success": "✅"}.get(card.get('severity'), "❓")
    print(f"  {severity_icon} [{card.get('type')}] {card.get('title')}")
    print(f"     {card.get('message')}")

# Verify we have at least some insights
assert len(cards) > 0, "No insight cards generated!"
print("\n✅ Insight cards working")
```

**Expected insights from our data:**
- Spending spikes (any category > 30% above average)
- Price increases (Netflix, etc. if amount changed)
- Unused subscriptions (if any recurring series stopped)

**If issues found:**
- No cards → Check detection logic thresholds
- Wrong cards → Verify SQL queries for patterns
- Missing types → Implement all detection functions

---

### B.5 Transaction Review Feature

**API Endpoints to test:**
```bash
# Get unreviewed transactions
curl http://localhost:8000/api/transactions/unreviewed

# Mark single as reviewed
curl -X POST http://localhost:8000/api/transactions/{tx_id}/review

# Bulk mark as reviewed
curl -X POST http://localhost:8000/api/transactions/bulk/review \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": ["id1", "id2", "id3"]}'

# Get reviewed transactions
curl "http://localhost:8000/api/transactions?reviewed=true"
```

**Validation checklist:**
- [ ] reviewed_at column exists in database
- [ ] Can mark single transaction
- [ ] Can bulk mark transactions
- [ ] Filter by reviewed status works
- [ ] Timestamp is set correctly

**Test with real data:**
```python
import requests

# Get unreviewed count
unreviewed = requests.get("http://localhost:8000/api/transactions/unreviewed?limit=1").json()
total_unreviewed = unreviewed.get('total', 0)
print(f"Unreviewed transactions: {total_unreviewed}")

# Get sample to review
sample = requests.get("http://localhost:8000/api/transactions?limit=5").json()
tx_ids = [tx['id'] for tx in sample.get('items', [])]

if tx_ids:
    # Mark first one as reviewed
    response = requests.post(f"http://localhost:8000/api/transactions/{tx_ids[0]}/review")
    print(f"Marked as reviewed: {response.status_code}")
    
    # Verify it's now reviewed
    tx = requests.get(f"http://localhost:8000/api/transactions/{tx_ids[0]}").json()
    assert tx.get('reviewed_at') is not None, "reviewed_at not set!"
    print(f"✅ Single review works - reviewed_at: {tx.get('reviewed_at')}")
    
    # Bulk review
    if len(tx_ids) > 1:
        bulk_response = requests.post(
            "http://localhost:8000/api/transactions/bulk/review",
            json={"transaction_ids": tx_ids[1:]}
        )
        print(f"Bulk reviewed {len(tx_ids)-1} transactions: {bulk_response.status_code}")

# Check reviewed count increased
reviewed = requests.get("http://localhost:8000/api/transactions?reviewed=true&limit=1").json()
print(f"Reviewed transactions now: {reviewed.get('total', 0)}")
```

**If issues found:**
- Column missing → Add migration for reviewed_at
- Endpoint missing → Create in routes/transactions.py
- Filter not working → Add to transaction query builder

---

## PART C: INTEGRATION TESTING

### C.1 Dashboard Integration

**Test that dashboard pulls from all features:**

```bash
# All these should return data for dashboard
curl http://localhost:8000/api/networth          # Net worth card
curl http://localhost:8000/api/insights/cards    # Insight feed
curl http://localhost:8000/api/calendar/upcoming # Upcoming bills
curl http://localhost:8000/api/transactions?limit=10  # Recent transactions
curl http://localhost:8000/api/analytics/spending/monthly  # Cash flow
```

### C.2 Calendar + Recurring Integration

**Verify calendar uses recurring data:**

```python
import requests

recurring = requests.get("http://localhost:8000/api/recurring").json()
calendar = requests.get("http://localhost:8000/api/calendar/upcoming?days=60").json()

# Every calendar item should reference a recurring series
recurring_ids = {r['id'] for r in recurring}
for bill in calendar:
    series_id = bill.get('recurring_series_id') or bill.get('series_id')
    if series_id:
        assert series_id in recurring_ids, f"Calendar item references unknown series: {series_id}"

print(f"✅ All {len(calendar)} calendar items reference valid recurring series")
```

### C.3 Budget + Categories Integration

**Verify budget uses correct categories:**

```python
import requests

categories = requests.get("http://localhost:8000/api/categories").json()
cat_ids = {c['id'] for c in categories}

# Create budget and try invalid category
budget = requests.post(
    "http://localhost:8000/api/budgets",
    json={"name": "Integration Test", "period": "monthly"}
).json()

# Should reject invalid category
invalid = requests.post(
    f"http://localhost:8000/api/budgets/{budget['id']}/categories",
    json={"category_id": "FAKE_CAT_ID", "amount_limit": 100}
)
assert invalid.status_code in [400, 404], "Should reject invalid category!"
print("✅ Budget rejects invalid categories")

# Clean up
requests.delete(f"http://localhost:8000/api/budgets/{budget['id']}")
```

### C.4 Insights + Transactions Integration

**Verify insights reference real transactions:**

```python
import requests

cards = requests.get("http://localhost:8000/api/insights/cards").json()

for card in cards:
    if card.get('action_url'):
        # Action URL should be valid
        if '/transactions?' in card['action_url']:
            # Try to fetch those transactions
            url = f"http://localhost:8000/api{card['action_url']}&limit=1"
            response = requests.get(url)
            assert response.status_code == 200, f"Invalid action URL: {card['action_url']}"

print(f"✅ All insight action URLs are valid")
```

---

## PART D: GENERATE REPORTS

### D.1 Feature Test Report

```markdown
## KASHAT_FEATURE_TEST_REPORT.md

### Test Date: [DATE]
### Data: 2,118 transactions, 61 recurring series

---

## Net Worth Feature

| Test | Status | Notes |
|------|--------|-------|
| Endpoint exists | ✅/❌ | |
| Account types correct | ✅/❌ | |
| Calculation correct | ✅/❌ | |
| History works | ✅/❌ | |

**Issues Found:**
- 

---

## Bill Calendar Feature

| Test | Status | Notes |
|------|--------|-------|
| Endpoint exists | ✅/❌ | |
| Uses recurring data | ✅/❌ | |
| Sorted by date | ✅/❌ | |
| Shows correct amounts | ✅/❌ | |

**Issues Found:**
-

---

## Budget System Feature

| Test | Status | Notes |
|------|--------|-------|
| Create budget | ✅/❌ | |
| Set category limits | ✅/❌ | |
| Progress calculation | ✅/❌ | |
| Over-budget detection | ✅/❌ | |

**Issues Found:**
-

---

## Smart Insights Feature

| Test | Status | Notes |
|------|--------|-------|
| Cards generated | ✅/❌ | |
| Spending spikes | ✅/❌ | |
| Price increases | ✅/❌ | |
| Unused subscriptions | ✅/❌ | |

**Issues Found:**
-

---

## Transaction Review Feature

| Test | Status | Notes |
|------|--------|-------|
| Mark reviewed | ✅/❌ | |
| Bulk review | ✅/❌ | |
| Filter works | ✅/❌ | |
| Timestamp set | ✅/❌ | |

**Issues Found:**
-

---

## Integration Tests

| Test | Status |
|------|--------|
| Dashboard pulls all data | ✅/❌ |
| Calendar uses recurring | ✅/❌ |
| Budget validates categories | ✅/❌ |
| Insights link to transactions | ✅/❌ |

---

## Overall Status

| Feature | Status |
|---------|--------|
| Net Worth | PASS/FAIL |
| Bill Calendar | PASS/FAIL |
| Budget System | PASS/FAIL |
| Smart Insights | PASS/FAIL |
| Transaction Review | PASS/FAIL |

**All Features Working**: ✅ YES / ❌ NO
```

### D.2 Pipeline Audit Report

```markdown
## PIPELINE_AUDIT_REPORT.md

### Current Pipeline Sequence

| Order | Stage | File | Correct Order? |
|-------|-------|------|----------------|
| 1 | Import | | ✅/❌ |
| 2 | Deduplicate | | ✅/❌ |
| 3 | Categorize | | ✅/❌ |
| 4 | Transfer Detection | | ✅/❌ |
| 5 | P2P Detection | | ✅/❌ |
| 6 | Recurring Detection | | ✅/❌ |
| 7 | Enrichment | | ✅/❌ |
| 8 | Quality Check | | ✅/❌ |

### Issues Found

1. **[Issue]**
   - Current behavior: 
   - Expected behavior:
   - Fix required:

### Recommendations

-
```

---

## EXECUTION CHECKLIST

```
[ ] Part A: Pipeline Audit
    [ ] Documented current order
    [ ] Verified against expected order
    [ ] Identified issues
    [ ] Fixed if needed

[ ] Part B: Feature Tests
    [ ] Net Worth tested
    [ ] Calendar tested
    [ ] Budget tested
    [ ] Insights tested
    [ ] Review tested

[ ] Part C: Integration Tests
    [ ] Dashboard integration
    [ ] Calendar + Recurring
    [ ] Budget + Categories
    [ ] Insights + Transactions

[ ] Part D: Reports Generated
    [ ] Feature test report
    [ ] Pipeline audit report
    [ ] All issues documented
```

---

## SUCCESS CRITERIA

| Test | Target |
|------|--------|
| Pipeline order correct | All 8 stages in order |
| Net Worth feature | All tests pass |
| Calendar feature | All tests pass |
| Budget feature | All tests pass |
| Insights feature | All tests pass |
| Review feature | All tests pass |
| Integration tests | All pass |

---

*Test each feature thoroughly. Fix issues as you find them. Document everything.*
