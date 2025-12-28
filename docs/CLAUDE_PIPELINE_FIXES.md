# KASHAT PIPELINE & FEATURE FIXES
## For Claude Code CLI

---

## CONTEXT

Feature validation completed with 26/28 tests passing (93%).
Pipeline audit found 2 stages need automation.

**Location**: `C:\Users\Marwan\Desktop\AI\Flos`

---

## ISSUES TO FIX

### Issue 1: Transfer Detection Not Automated (CRITICAL)

**Problem**: Transfer detection is not part of the automated post-import pipeline. This means:
- Transfers are counted in recurring detection (wrong!)
- User must manually trigger transfer detection
- Internal movements inflate spending totals

**Location**: Find `_run_builtin_detectors()` in the import/ingest workflow

**Fix Required**:
```python
async def _run_builtin_detectors(self, import_run_id: str, conn):
    """Run all detection pipelines in correct order."""
    
    # EXISTING (keep these)
    await self._run_deduplication(...)
    await self._run_ai_enhancement(...)
    await self._run_categorization(...)
    
    # ADD THIS - Transfer detection BEFORE recurring
    await self._run_transfer_detection(import_run_id, conn)
    
    # ADD THIS - P2P detection BEFORE recurring  
    await self._run_p2p_detection(import_run_id, conn)
    
    # EXISTING - Recurring AFTER transfers/P2P excluded
    await self._run_recurring_detection(...)
    
    # EXISTING (keep these)
    await self._run_enrichment(...)
    await self._run_quality_check(...)
```

**Implementation**:
```python
async def _run_transfer_detection(self, import_run_id: str, conn):
    """Detect internal transfers between accounts."""
    from kashat.services.transfers import TransferDetectionService
    
    logger.info(f"Running transfer detection for import {import_run_id}")
    
    service = TransferDetectionService(conn)
    
    # Get transactions from this import run
    tx_ids = self._get_import_run_transactions(import_run_id, conn)
    
    if tx_ids:
        result = await service.detect_transfers(transaction_ids=tx_ids)
        logger.info(f"Transfer detection complete: {result.get('matches_found', 0)} pairs")
    
    return result
```

---

### Issue 2: P2P Detection Only Partial (CRITICAL)

**Problem**: Only Zelle detection runs automatically. Venmo, CashApp, PayPal, Western Union, Wire are on-demand only.

**Location**: Find P2P detection logic, likely in:
- `services/p2p.py` or `services/p2p_detection.py`
- `ai/detection.py` (after consolidation)

**Fix Required**:
```python
async def _run_p2p_detection(self, import_run_id: str, conn):
    """Detect all P2P payment types."""
    from kashat.services.p2p import P2PDetectionService
    
    logger.info(f"Running P2P detection for import {import_run_id}")
    
    service = P2PDetectionService(conn)
    
    # Get transactions from this import run
    tx_ids = self._get_import_run_transactions(import_run_id, conn)
    
    if tx_ids:
        # Detect ALL P2P types, not just Zelle
        result = await service.detect_all_p2p(
            transaction_ids=tx_ids,
            platforms=['zelle', 'venmo', 'cashapp', 'paypal', 'western_union', 'wire']
        )
        logger.info(f"P2P detection complete: {result.get('total_detected', 0)} transactions")
    
    return result
```

**Verify P2P patterns include all platforms**:
```python
P2P_PATTERNS = {
    'zelle': [
        r'zelle\s+(to|from|payment)',
        r'zelle\s+\w+',
        r'(?:sent|received)\s+.*zelle',
    ],
    'venmo': [
        r'venmo\s+(payment|transfer|cashout)',
        r'venmo\s+\*',
        r'venmo\.com',
    ],
    'cashapp': [
        r'cash\s*app',
        r'square\s+cash',
        r'\*sq\s*\*cash',
        r'cash\s+out.*square',
    ],
    'paypal': [
        r'paypal\s+(transfer|payment|instant)',
        r'paypal\s+\*',
        r'pp\s*\*',
    ],
    'western_union': [
        r'western\s+union',
        r'wu\s+transfer',
        r'westernunion',
    ],
    'wire': [
        r'wire\s+(transfer|in|out)',
        r'incoming\s+wire',
        r'outgoing\s+wire',
        r'fed\s*wire',
    ],
}
```

---

### Issue 3: Account Type Not Set (HIGH)

**Problem**: Account type shows "unknown" instead of "checking", "savings", "credit_card", etc.

**Location**: 
- Import service where accounts are created
- Account model/schema

**Fix Required - Auto-detect during import**:
```python
def _detect_account_type(self, account_name: str, filename: str = None) -> str:
    """Auto-detect account type from name and filename."""
    name_lower = account_name.lower()
    file_lower = (filename or '').lower()
    combined = f"{name_lower} {file_lower}"
    
    # Credit cards
    if any(x in combined for x in ['credit', 'visa', 'mastercard', 'amex', 'discover', 'card']):
        return 'credit_card'
    
    # Savings
    if any(x in combined for x in ['saving', 'savings', 'money market', 'mma']):
        return 'savings'
    
    # Loans
    if any(x in combined for x in ['loan', 'mortgage', 'auto', 'student', 'personal loan']):
        return 'loan'
    
    # Investment
    if any(x in combined for x in ['investment', 'brokerage', 'ira', '401k', 'roth']):
        return 'investment'
    
    # Default to checking
    return 'checking'
```

**Apply during account creation**:
```python
def get_or_create_account(self, conn, account_name: str, filename: str = None) -> Account:
    """Get existing account or create new one with auto-detected type."""
    
    existing = self._get_account_by_name(conn, account_name)
    if existing:
        # Update type if still unknown
        if existing.account_type == 'unknown':
            detected_type = self._detect_account_type(account_name, filename)
            self._update_account_type(conn, existing.id, detected_type)
            existing.account_type = detected_type
        return existing
    
    # Create new account with detected type
    account_type = self._detect_account_type(account_name, filename)
    
    return self._create_account(
        conn,
        name=account_name,
        account_type=account_type
    )
```

**Fix existing data - Run once**:
```sql
-- Update existing accounts with "unknown" type
UPDATE account SET account_type = 
    CASE 
        WHEN lower(name) LIKE '%credit%' THEN 'credit_card'
        WHEN lower(name) LIKE '%visa%' THEN 'credit_card'
        WHEN lower(name) LIKE '%mastercard%' THEN 'credit_card'
        WHEN lower(name) LIKE '%amex%' THEN 'credit_card'
        WHEN lower(name) LIKE '%saving%' THEN 'savings'
        WHEN lower(name) LIKE '%loan%' THEN 'loan'
        WHEN lower(name) LIKE '%mortgage%' THEN 'loan'
        WHEN lower(name) LIKE '%auto%' THEN 'loan'
        ELSE 'checking'
    END
WHERE account_type IS NULL OR account_type = 'unknown';
```

---

### Issue 4: API Field Naming Inconsistency (MEDIUM)

**Problem**: Bulk review endpoint uses `tx_ids` but should use `transaction_ids` for consistency.

**Location**: `routes/transactions.py` - bulk review endpoint

**Fix Required**:
```python
# BEFORE (inconsistent)
class BulkReviewRequest(BaseModel):
    tx_ids: list[str]

@router.post("/transactions/bulk/review")
def bulk_review(request: BulkReviewRequest, ...):
    for tx_id in request.tx_ids:
        ...

# AFTER (consistent with other endpoints)
class BulkReviewRequest(BaseModel):
    transaction_ids: list[str]
    
    # Keep backward compatibility
    @validator('transaction_ids', pre=True, always=True)
    def accept_tx_ids(cls, v, values):
        return v

@router.post("/transactions/bulk/review")
def bulk_review(request: BulkReviewRequest, ...):
    for tx_id in request.transaction_ids:
        ...
```

**Also check and fix any other inconsistencies**:
- Search for `tx_id` vs `transaction_id` patterns
- Search for `cat_id` vs `category_id` patterns
- Standardize all API field names

---

## EXECUTION ORDER

```
1. Fix Pipeline Order (Issues 1 & 2)
   ├── Locate _run_builtin_detectors() or equivalent
   ├── Add transfer detection step
   ├── Add full P2P detection step
   ├── Ensure order: transfers → P2P → recurring
   └── Test with existing data

2. Fix Account Type Detection (Issue 3)
   ├── Add _detect_account_type() function
   ├── Apply during account creation
   ├── Run SQL to fix existing accounts
   └── Verify net worth now shows proper types

3. Fix API Consistency (Issue 4)
   ├── Update bulk review endpoint
   ├── Search for other inconsistencies
   ├── Fix any found
   └── Update any frontend calls if needed

4. Re-run Validation
   ├── Run transfer detection on all transactions
   ├── Run P2P detection on all transactions
   ├── Verify pipeline runs in correct order
   └── Confirm all 28 tests now pass
```

---

## VALIDATION

### After Fix 1 & 2 (Pipeline):
```bash
# Clear and re-import one file to test pipeline
curl -X POST http://localhost:8000/api/import/upload \
  -F "file=@bank/test_statement.pdf"

# Check transfers were auto-detected
curl http://localhost:8000/api/transfers
# Should show matches if applicable

# Check P2P was auto-detected  
curl http://localhost:8000/api/p2p
# Should show all platforms, not just Zelle

# Check recurring doesn't include transfers
curl http://localhost:8000/api/recurring
# Transfers should be excluded
```

### After Fix 3 (Account Types):
```bash
# Check accounts have proper types
curl http://localhost:8000/api/accounts
# Should show checking/savings/credit_card, not "unknown"

# Check net worth calculation
curl http://localhost:8000/api/networth
# Should properly categorize assets vs liabilities
```

### After Fix 4 (API Consistency):
```bash
# Test bulk review with correct field name
curl -X POST http://localhost:8000/api/transactions/bulk/review \
  -H "Content-Type: application/json" \
  -d '{"transaction_ids": ["id1", "id2"]}'
# Should work

# Old field name should still work (backward compat)
curl -X POST http://localhost:8000/api/transactions/bulk/review \
  -H "Content-Type: application/json" \
  -d '{"tx_ids": ["id1", "id2"]}'
# Should also work
```

---

## RE-RUN FULL VALIDATION

After all fixes, run the feature validation again:

```python
# Quick validation script
import requests

results = {}

# Test 1: Transfer detection automated
# Import a file and check transfers detected without manual trigger
results['transfer_auto'] = "PASS" if ... else "FAIL"

# Test 2: P2P detection all platforms
p2p = requests.get("http://localhost:8000/api/p2p").json()
platforms = set(p.get('platform') for p in p2p)
results['p2p_all'] = "PASS" if platforms >= {'zelle', 'venmo', 'cashapp'} else "FAIL"

# Test 3: Account types set
accounts = requests.get("http://localhost:8000/api/accounts").json()
unknown = [a for a in accounts if a.get('account_type') == 'unknown']
results['account_types'] = "PASS" if len(unknown) == 0 else "FAIL"

# Test 4: API consistency
bulk = requests.post(
    "http://localhost:8000/api/transactions/bulk/review",
    json={"transaction_ids": ["test"]}
)
results['api_consistency'] = "PASS" if bulk.status_code in [200, 404] else "FAIL"

print("\n=== FIX VALIDATION ===")
for test, result in results.items():
    icon = "✅" if result == "PASS" else "❌"
    print(f"{icon} {test}: {result}")

all_pass = all(r == "PASS" for r in results.values())
print(f"\nAll fixes verified: {'✅ YES' if all_pass else '❌ NO'}")
```

---

## SUCCESS CRITERIA

| Issue | Fix Applied | Verified |
|-------|-------------|----------|
| Transfer detection automated | ✅ | ✅ |
| P2P detection all platforms | ✅ | ✅ |
| Account types auto-detected | ✅ | ✅ |
| API field names consistent | ✅ | ✅ |

**Target: 28/28 tests passing (100%)**
**Target: Pipeline health 100%**

---

*Fix each issue. Test after each fix. Achieve 100% across the board.*
