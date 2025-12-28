# LedgerLoop Comprehensive QA & Bug Hunt

## YOUR ROLE

You are a **ruthless Senior QA Engineer**. Your reputation is built on finding bugs others miss. You will systematically test every aspect of LedgerLoop and fix ALL issues you find.

**Your mindset:**
- ASSUME NOTHING WORKS until proven
- Test EDGE CASES, not just happy paths
- Check LOGS for hidden errors
- Verify DATA INTEGRITY
- Test ERROR HANDLING
- Find PERFORMANCE issues
- Leave NO STONE UNTURNED
- FIX issues as you find them

---

## PHASE 1: ENVIRONMENT HEALTH (5 min)

### 1.1 Verify Services
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Both containers should show "healthy" or "Up".

### 1.2 Check Startup Errors
```bash
# Backend errors
docker logs ledgerloop-backend 2>&1 | grep -i -E "(error|exception|traceback|failed|critical)" | tail -30

# Frontend errors  
docker logs ledgerloop-web 2>&1 | grep -i -E "(error|failed|cannot)" | tail -20
```

**If ANY startup errors exist, investigate and fix them first.**

### 1.3 Database Health
```bash
# Transaction count
curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total'

# Category count
curl -s "http://localhost:8000/api/categories" | jq 'length'

# AI stats
curl -s "http://localhost:8000/api/ai/stats" | jq .
```

---

## PHASE 2: API DEEP TESTING (20 min)

### 2.1 Core Endpoints - Full Response Validation

Test each endpoint and validate the response structure:

```bash
# Health - should have status, version, timestamp
curl -s http://localhost:8000/api/health | jq 'keys'

# Transactions - should have data array and meta
curl -s "http://localhost:8000/api/transactions?limit=5" | jq 'keys'

# Categories - should be array with id, name, parent_id
curl -s http://localhost:8000/api/categories | jq '.[0] | keys'

# Rules - check structure
curl -s http://localhost:8000/api/rules | jq '.[0] | keys' 2>/dev/null || echo "No rules yet"

# Settings - check structure
curl -s http://localhost:8000/api/settings | jq 'keys'
```

### 2.2 Intelligence Endpoints - Validate AI Output

```bash
# Health score - must have overall_score 0-100
HEALTH=$(curl -s http://localhost:8000/api/intelligence/health)
echo "$HEALTH" | jq '.health_report.overall_score'
SCORE=$(echo "$HEALTH" | jq '.health_report.overall_score')
if [ "$SCORE" -lt 0 ] || [ "$SCORE" -gt 100 ]; then
    echo "ERROR: Invalid health score: $SCORE"
fi

# Insights - must have insights array
curl -s http://localhost:8000/api/intelligence/insights | jq '.insights | length'

# Behavior - must have persona
curl -s http://localhost:8000/api/intelligence/behavior | jq '.behavior_profile.persona'

# Subscriptions - check structure
curl -s http://localhost:8000/api/intelligence/subscriptions | jq '.summary'
```

### 2.3 Analytics Endpoints
```bash
# Dashboard
curl -s http://localhost:8000/api/analytics/dashboard | jq 'keys'

# Monthly
curl -s http://localhost:8000/api/analytics/monthly | jq 'length'

# Spending patterns
curl -s http://localhost:8000/api/analytics/ai/spending-patterns | jq 'length'

# Trends
curl -s http://localhost:8000/api/analytics/ai/trends | jq 'length'

# Anomalies
curl -s http://localhost:8000/api/analytics/ai/anomalies | jq 'length'
```

### 2.4 Edge Case Testing
```bash
# Empty/Invalid parameters
curl -s "http://localhost:8000/api/transactions?limit=0" | jq '.data | length'
curl -s "http://localhost:8000/api/transactions?limit=-1" | jq .
curl -s "http://localhost:8000/api/transactions?limit=10000" | jq '.data | length'

# Invalid UUIDs
curl -s "http://localhost:8000/api/transactions/not-a-uuid" | jq .
curl -s "http://localhost:8000/api/categories/invalid-id" | jq .

# Missing required fields
curl -s -X POST "http://localhost:8000/api/categories" -H "Content-Type: application/json" -d '{}' | jq .
```

---

## PHASE 3: DATA INTEGRITY (15 min)

### 3.1 Transaction Consistency
```bash
# Total should equal categorized + uncategorized
TOTAL=$(curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total')
CATEGORIZED=$(curl -s "http://localhost:8000/api/transactions?limit=1&has_category=true" | jq '.meta.total // .total')
UNCATEGORIZED=$(curl -s "http://localhost:8000/api/transactions?limit=1&has_category=false" | jq '.meta.total // .total')

echo "Total: $TOTAL"
echo "Categorized: $CATEGORIZED"
echo "Uncategorized: $UNCATEGORIZED"
echo "Sum: $((CATEGORIZED + UNCATEGORIZED))"

if [ "$TOTAL" != "$((CATEGORIZED + UNCATEGORIZED))" ]; then
    echo "ERROR: Transaction count mismatch!"
fi
```

### 3.2 Category Integrity
```bash
# Find orphan categories (no transactions)
curl -s http://localhost:8000/api/categories | jq '[.[] | select(.transaction_count == 0)] | length'

# Find categories with transactions but no parent
curl -s http://localhost:8000/api/categories | jq '[.[] | select(.parent_id == null and .transaction_count > 0)] | .[].name'
```

### 3.3 Recurring Data Integrity
```bash
# Check recurring series
curl -s http://localhost:8000/api/recurring | jq 'length'

# Check for recurring with negative amounts (should be expenses)
curl -s http://localhost:8000/api/recurring | jq '[.[] | select(.amount_mean > 0)] | length'
```

### 3.4 Transfer Integrity
```bash
# Check transfers
curl -s http://localhost:8000/api/transfers | jq 'length'

# Check for unbalanced transfers (amounts should net to ~0)
curl -s http://localhost:8000/api/transfers | jq '.[0] | {left: .left_amount, right: .right_amount, sum: (.left_amount + .right_amount)}'
```

---

## PHASE 4: FRONTEND TESTING (15 min)

### 4.1 Page Load Tests
```bash
BASE="http://localhost:3000"
for page in "/" "/transactions" "/categories" "/rules" "/recurring" "/transfers" "/ai" "/ingest" "/settings"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$page")
    if [ "$status" == "200" ]; then
        echo "OK  $page"
    else
        echo "FAIL $page ($status)"
    fi
done
```

### 4.2 Check for Build/TypeScript Errors
```bash
cd apps/web
npx tsc --noEmit 2>&1 | head -30
```

Fix any TypeScript errors found.

### 4.3 Browser Console Check

Open each page in browser and check DevTools Console (F12):
1. http://localhost:3000/ (Dashboard)
2. http://localhost:3000/transactions
3. http://localhost:3000/categories
4. http://localhost:3000/recurring
5. http://localhost:3000/transfers
6. http://localhost:3000/settings

Document any JavaScript errors or failed network requests.

---

## PHASE 5: AI SYSTEM VALIDATION (15 min)

### 5.1 AI Configuration Check
```bash
curl -s http://localhost:8000/api/settings | jq '{
    ai_provider: .ai_provider,
    auto_categorize: .ai_auto_categorize_on_import,
    min_confidence: .ai_auto_categorize_min_conf
}'
```

### 5.2 AI Categorization Test
```bash
# Get an uncategorized transaction
TX=$(curl -s "http://localhost:8000/api/transactions?has_category=false&limit=1" | jq -r '.data[0]')
TX_ID=$(echo "$TX" | jq -r '.id')
TX_DESC=$(echo "$TX" | jq -r '.description')

if [ "$TX_ID" != "null" ] && [ -n "$TX_ID" ]; then
    echo "Testing AI on: $TX_DESC"
    
    # Analyze it
    RESULT=$(curl -s -X POST "http://localhost:8000/api/ai/analyze/transaction/$TX_ID")
    echo "$RESULT" | jq '{
        merchant: .merchant_name,
        confidence: .confidence,
        suggestions: [.category_suggestions[]?.name][:3]
    }'
else
    echo "No uncategorized transactions to test"
fi
```

### 5.3 Intelligence Quality Check
```bash
# Health score should be reasonable
SCORE=$(curl -s http://localhost:8000/api/intelligence/health | jq '.health_report.overall_score')
echo "Health Score: $SCORE"

# Should have recommendations
RECS=$(curl -s http://localhost:8000/api/intelligence/health | jq '.health_report.recommendations | length')
echo "Recommendations: $RECS"

# Insights should have content
INSIGHTS=$(curl -s http://localhost:8000/api/intelligence/insights | jq '.insights | length')
echo "Insights generated: $INSIGHTS"

# Behavior should detect a persona
PERSONA=$(curl -s http://localhost:8000/api/intelligence/behavior | jq -r '.behavior_profile.persona')
echo "Detected persona: $PERSONA"
```

### 5.4 AI Detection Tests
```bash
# Recurring detection
RECURRING=$(curl -s -X POST "http://localhost:8000/api/intelligence/recurring/detect")
echo "Recurring candidates: $(echo "$RECURRING" | jq '.total_candidates')"

# Transfer suggestions
TRANSFERS=$(curl -s -X POST "http://localhost:8000/api/intelligence/transfers/suggest")
echo "Transfer suggestions: $(echo "$TRANSFERS" | jq '.total_suggestions')"

# Rule suggestions
RULES=$(curl -s http://localhost:8000/api/intelligence/rules/suggest)
echo "Rule suggestions: $(echo "$RULES" | jq '.total_suggestions')"
```

---

## PHASE 6: ERROR LOG ANALYSIS (10 min)

### 6.1 Backend Error Scan
```bash
# Count errors in last hour
docker logs ledgerloop-backend --since 1h 2>&1 | grep -c -i -E "(error|exception|traceback)" || echo "0"

# Show unique errors
docker logs ledgerloop-backend --since 1h 2>&1 | grep -i -E "(error|exception|traceback)" | sort | uniq -c | sort -rn | head -10
```

### 6.2 Categorize and Fix Errors

For each error type:
1. Find the source file
2. Understand root cause
3. Fix the issue
4. Restart backend
5. Verify fix

---

## PHASE 7: PERFORMANCE TESTING (10 min)

### 7.1 Response Time Check
```bash
echo "=== Response Times ==="

for endpoint in "/api/health" "/api/transactions?limit=50" "/api/categories" "/api/analytics/dashboard" "/api/intelligence/health"; do
    TIME=$(curl -s -o /dev/null -w "%{time_total}" "http://localhost:8000$endpoint")
    MS=$(echo "$TIME * 1000" | bc | cut -d. -f1)
    if [ "$MS" -lt 500 ]; then
        echo "OK  ${MS}ms - $endpoint"
    elif [ "$MS" -lt 2000 ]; then
        echo "SLOW ${MS}ms - $endpoint"
    else
        echo "CRITICAL ${MS}ms - $endpoint"
    fi
done
```

### 7.2 Large Data Test
```bash
# Test with large limit
time curl -s "http://localhost:8000/api/transactions?limit=500" > /dev/null
```

---

## PHASE 8: FIX ALL ISSUES

For each issue found:

```
1. REPRODUCE - Exact steps to trigger
2. DIAGNOSE - Find source code, identify root cause
3. FIX - Make minimal change
4. VERIFY - Test the fix works
5. REGRESSION - Ensure nothing else broke
6. DOCUMENT - Record what was fixed
```

---

## PHASE 9: FINAL VERIFICATION (10 min)

### 9.1 Complete Test Suite
```bash
echo "========================================="
echo "LEDGERLOOP FINAL VERIFICATION"
echo "========================================="

PASS=0
FAIL=0

check() {
    local name=$1
    local result=$2
    local expected=$3
    
    if [ "$result" == "$expected" ] || [ -n "$result" -a "$expected" == "NOT_EMPTY" ]; then
        echo "OK $name"
        PASS=$((PASS+1))
    else
        echo "FAIL $name (got: $result)"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Services ==="
check "Backend HTTP" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/health)" "200"
check "Frontend HTTP" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000)" "200"

echo "=== Core API ==="
check "Transactions" "$(curl -s -o /dev/null -w '%{http_code}' 'http://localhost:8000/api/transactions?limit=1')" "200"
check "Categories" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/categories)" "200"
check "Rules" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/rules)" "200"
check "Settings" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/settings)" "200"

echo "=== Intelligence ==="
check "Health Score" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/intelligence/health)" "200"
check "Insights" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/intelligence/insights)" "200"
check "Behavior" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/intelligence/behavior)" "200"
check "Subscriptions" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/intelligence/subscriptions)" "200"

echo "=== Analytics ==="
check "Dashboard" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/analytics/dashboard)" "200"
check "Patterns" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/analytics/ai/spending-patterns)" "200"

echo "=== Data ==="
check "Has Transactions" "$(curl -s 'http://localhost:8000/api/transactions?limit=1' | jq '.meta.total // .total // 0')" "NOT_EMPTY"
check "Health Score Valid" "$(curl -s http://localhost:8000/api/intelligence/health | jq '.health_report.overall_score >= 0 and .health_report.overall_score <= 100')" "true"

echo ""
echo "========================================="
echo "RESULTS: $PASS passed, $FAIL failed"
echo "========================================="
```

---

## OUTPUT FILES REQUIRED

### 1. QA_REPORT.md
```markdown
# LedgerLoop QA Report
Date: [DATE]

## Summary
- Tests Run: X
- Passed: X  
- Failed: X
- Fixed: X

## Issues Found & Fixed
[List each issue with: Location, Symptom, Root Cause, Fix, Verification]

## Remaining Issues
[Any issues not fixed and why]

## Performance
[Response times, slow endpoints]

## Recommendations
[Future improvements]
```

### 2. QA_TEST_LOG.md
Full output of all test commands.

---

## RULES

1. **TEST EVERYTHING** - Don't assume it works
2. **FIX AS YOU GO** - Don't just document, fix it
3. **VERIFY FIXES** - Test that fixes work
4. **DON'T BREAK THINGS** - Run regression tests
5. **BE THOROUGH** - Edge cases, error handling
6. **DOCUMENT EVERYTHING** - Create detailed reports

---

## SUCCESS CRITERIA

- [ ] ALL API endpoints return expected responses
- [ ] ALL frontend pages load without errors
- [ ] NO JavaScript console errors
- [ ] NO Python exceptions in logs (zero recurring errors)
- [ ] Data integrity checks pass
- [ ] AI endpoints return valid, meaningful data
- [ ] Response times < 2 seconds
- [ ] Health score is reasonable (not 0 or 100)
- [ ] Insights/recommendations are generated

---

## BEGIN

Start with Phase 1. Be ruthless. Find every bug. Fix everything. Leave the codebase spotless.

**GO.**
