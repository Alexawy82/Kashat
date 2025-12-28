# LedgerLoop Pipeline Execution & Live Debugging

## WHO YOU ARE

You are a **Senior Data Engineer & Debugger**. Your approach:
- Run real pipelines with real data
- Watch for failures in real-time
- Fix root causes, not symptoms
- Verify fixes with the actual data
- Leave the system fully populated and working

## THE MISSION

1. **Import ALL bank statements** from the `bank/` folder
2. **Run EVERY pipeline** (categorization, recurring detection, transfer matching, etc.)
3. **Fix issues AS THEY HAPPEN** - root cause analysis, surgical fixes
4. **Verify data integrity** - all transactions imported, categorized, analyzed
5. **Leave the app production-ready** with real, populated data

## CONTEXT

- Bank statements location: `bank/` folder in project root
- Database: DuckDB at `~/.ledgerloop/ledgerloop.duckdb` (or `/data/` in Docker)
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- Auth: DISABLED (single-user mode)

---

## PHASE 0: RECONNAISSANCE

### 0.1 Check Current State
```bash
# Is the app running?
docker ps | grep ledgerloop
curl -s http://localhost:8000/api/health | jq .

# If not running, start it:
cd /path/to/Flos
docker-compose up -d
sleep 15
```

### 0.2 Explore Bank Statements
```bash
# What files do we have?
ls -la bank/
find bank/ -type f -name "*.pdf" -o -name "*.csv" -o -name "*.PDF" -o -name "*.CSV"

# How many files?
find bank/ -type f | wc -l

# File types breakdown
find bank/ -type f | sed 's/.*\.//' | sort | uniq -c
```

### 0.3 Check Current Database State
```bash
# How many transactions already imported?
curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total // "unknown"'

# How many categories?
curl -s http://localhost:8000/api/categories | jq 'length'

# Import history
curl -s http://localhost:8000/api/import/runs | jq '.[-5:]'
```

**Document:** What you found - files available, current state, any immediate issues.

---

## PHASE 1: UNDERSTAND THE PIPELINES

### 1.1 Find All Pipeline Code
```bash
# Import/Ingest pipelines
ls -la apps/backend/src/ledgerloop/core/
cat apps/backend/src/ledgerloop/core/ingest*.py 2>/dev/null | head -100
cat apps/backend/src/ledgerloop/core/import*.py 2>/dev/null | head -100
cat apps/backend/src/ledgerloop/core/parser*.py 2>/dev/null | head -100

# Processing pipelines
cat apps/backend/src/ledgerloop/core/categoriz*.py 2>/dev/null | head -100
cat apps/backend/src/ledgerloop/core/recurring*.py 2>/dev/null | head -100
cat apps/backend/src/ledgerloop/core/transfer*.py 2>/dev/null | head -100

# AI pipelines
cat apps/backend/src/ledgerloop/core/ai*.py 2>/dev/null | head -100
```

### 1.2 Find API Endpoints for Pipelines
```bash
# Import endpoints
grep -rn "import\|ingest\|upload" apps/backend/src/ledgerloop/api/routes/ | head -30

# Processing endpoints
grep -rn "categorize\|recurring\|transfer\|detect" apps/backend/src/ledgerloop/api/routes/ | head -30
```

### 1.3 Document Available Pipelines

Create a list:
```
1. IMPORT PIPELINE: /api/ingest/upload or /api/import/file
   - Input: PDF/CSV bank statements
   - Output: Raw transactions in database

2. CATEGORIZATION PIPELINE: /api/ai/categorize or automatic
   - Input: Uncategorized transactions
   - Output: Transactions with category_id

3. RECURRING DETECTION: /api/recurring/detect
   - Input: All transactions
   - Output: Recurring series identified

4. TRANSFER MATCHING: /api/transfers/detect or /api/detect/zelle/preview
   - Input: All transactions
   - Output: Transfer pairs matched

5. RULES APPLICATION: /api/rules/apply
   - Input: Transactions + rules
   - Output: Transactions categorized by rules
```

---

## PHASE 2: RUN IMPORT PIPELINE

### 2.1 Test Import with One File First
```bash
# Pick one file to test
TEST_FILE=$(find bank/ -type f \( -name "*.pdf" -o -name "*.PDF" -o -name "*.csv" \) | head -1)
echo "Testing with: $TEST_FILE"

# Try the import endpoint
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@$TEST_FILE" \
  -v 2>&1 | tee /tmp/import_test.log

# Check the response
cat /tmp/import_test.log | tail -20
```

### 2.2 If Import Fails - Debug and Fix

**Common issues and fixes:**

**Issue: 404 Not Found**
```bash
# Find the correct endpoint
grep -rn "upload\|ingest" apps/backend/src/ledgerloop/api/routes/
# Fix: Use the correct endpoint path
```

**Issue: 500 Internal Server Error**
```bash
# Check Docker logs
docker logs ledgerloop-backend --tail 50 | grep -A5 "Error\|Exception"

# Common fixes:
# 1. PDF parsing error - check pdfplumber is installed
# 2. Database error - check DuckDB connection
# 3. File path error - check volume mounts
```

**Issue: File type not supported**
```bash
# Check what parsers exist
ls apps/backend/src/ledgerloop/core/parsers/
grep -rn "pdf\|csv\|PDF\|CSV" apps/backend/src/ledgerloop/core/
```

**Issue: DuckDB SQL Error**
```bash
# Look for the exact error
docker logs ledgerloop-backend 2>&1 | grep -i "sql\|syntax\|duckdb"

# Fix INSERT OR IGNORE -> ON CONFLICT
grep -rn "INSERT OR IGNORE" apps/backend/src/ledgerloop/
# Replace with: INSERT INTO ... ON CONFLICT DO NOTHING
```

### 2.3 Import All Files

Once single file works, import all:

```bash
#!/bin/bash
# Save as scripts/import-all.sh

IMPORT_URL="http://localhost:8000/api/ingest/upload"  # Adjust if different
BANK_DIR="bank"
SUCCESS=0
FAILED=0

echo "📂 Importing all bank statements..."
echo "=================================="

for file in $(find "$BANK_DIR" -type f \( -name "*.pdf" -o -name "*.PDF" -o -name "*.csv" -o -name "*.CSV" \)); do
    echo -n "Importing $file... "
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$IMPORT_URL" -F "file=@$file")
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" == "200" ] || [ "$http_code" == "201" ]; then
        echo "✅ OK"
        SUCCESS=$((SUCCESS+1))
    else
        echo "❌ FAILED (HTTP $http_code)"
        echo "  Response: $body"
        FAILED=$((FAILED+1))
    fi
done

echo ""
echo "=================================="
echo "✅ Successful: $SUCCESS"
echo "❌ Failed: $FAILED"
```

### 2.4 Verify Import Results
```bash
# Count transactions now
curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total'

# Check import runs
curl -s http://localhost:8000/api/import/runs | jq '.'

# Sample of imported transactions
curl -s "http://localhost:8000/api/transactions?limit=5" | jq '.data[:3]'
```

---

## PHASE 3: RUN CATEGORIZATION PIPELINE

### 3.1 Check Uncategorized Transactions
```bash
# How many need categorization?
curl -s "http://localhost:8000/api/transactions?has_category=false&limit=1" | jq '.meta.total // .total'

# Sample uncategorized
curl -s "http://localhost:8000/api/transactions?has_category=false&limit=5" | jq '.data[:3]'
```

### 3.2 Check Available Categories
```bash
curl -s http://localhost:8000/api/categories | jq '.[].name'

# If no categories, we need to bootstrap them
curl -s http://localhost:8000/api/categories | jq 'length'
```

### 3.3 Bootstrap Categories (if needed)
```bash
# Check if bootstrap endpoint exists
curl -s -X POST http://localhost:8000/api/categories/bootstrap

# Or run bootstrap script
python scripts/bootstrap_categories.py 2>/dev/null || echo "Script not found"

# Or create manually via API
curl -X POST http://localhost:8000/api/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Food & Dining", "type": "expense"}'
```

### 3.4 Run AI Categorization
```bash
# Check AI status
curl -s http://localhost:8000/api/ai/status | jq .

# If AI is available, run categorization
curl -s -X POST "http://localhost:8000/api/ai/categorize?limit=100" | jq .

# Check results
curl -s http://localhost:8000/api/ai/stats | jq .
```

### 3.5 Apply Rules-Based Categorization
```bash
# Check existing rules
curl -s http://localhost:8000/api/rules | jq '.'

# Get rule suggestions from existing data
curl -s http://localhost:8000/api/rules/suggestions | jq '.[:5]'

# Apply rules to transactions
curl -s -X POST http://localhost:8000/api/rules/apply | jq .
```

### 3.6 Debug Categorization Issues

**Issue: AI categorization not working**
```bash
# Check OpenAI API key
docker exec ledgerloop-backend env | grep OPENAI

# Check AI provider status
curl -s http://localhost:8000/api/ai/providers | jq .

# If no AI, rely on rules-based categorization
```

**Issue: Categories not being assigned**
```bash
# Check the categorization logic
cat apps/backend/src/ledgerloop/core/categorization.py | head -100

# Check for errors in logs
docker logs ledgerloop-backend 2>&1 | grep -i "categ" | tail -20
```

---

## PHASE 4: RUN RECURRING DETECTION

### 4.1 Trigger Recurring Detection
```bash
# Run detection
curl -s -X POST http://localhost:8000/api/recurring/detect | jq .

# Or if it's GET
curl -s http://localhost:8000/api/recurring/detect | jq .

# Check results
curl -s http://localhost:8000/api/recurring | jq '.[:5]'
curl -s http://localhost:8000/api/recurring/series | jq '.[:5]'
```

### 4.2 Verify Recurring Results
```bash
# Count detected subscriptions
curl -s http://localhost:8000/api/recurring | jq 'length'

# Monthly total
curl -s http://localhost:8000/api/recurring | jq '[.[] | .amount] | add'
```

### 4.3 Debug Recurring Issues

**Issue: No recurring transactions detected**
```bash
# Check the detection logic
cat apps/backend/src/ledgerloop/core/recurring*.py | head -150

# Check if there's enough data (need multiple months)
curl -s "http://localhost:8000/api/transactions?limit=5000" | jq '[.data[].date[:7]] | unique | length'
# Should be > 1 month of data

# Check for detection parameters
grep -rn "threshold\|min_occurrences\|frequency" apps/backend/src/ledgerloop/core/recurring*.py
```

---

## PHASE 5: RUN TRANSFER DETECTION

### 5.1 Trigger Transfer Detection
```bash
# Zelle detection
curl -s http://localhost:8000/api/detect/zelle/preview | jq '.[:5]'

# General transfer detection
curl -s -X POST http://localhost:8000/api/transfers/detect | jq .

# Check results
curl -s http://localhost:8000/api/transfers | jq '.[:5]'
```

### 5.2 Verify Transfer Results
```bash
# Count transfer pairs
curl -s http://localhost:8000/api/transfers | jq 'length'

# By status
curl -s "http://localhost:8000/api/transfers?status=pending" | jq 'length'
curl -s "http://localhost:8000/api/transfers?status=confirmed" | jq 'length'
```

### 5.3 Debug Transfer Issues

**Issue: Transfers not being detected**
```bash
# Check detection logic
cat apps/backend/src/ledgerloop/core/transfer*.py | head -150

# Check for matching criteria
grep -rn "zelle\|venmo\|transfer\|match" apps/backend/src/ledgerloop/core/
```

---

## PHASE 6: VERIFY ANALYTICS

### 6.1 Test All Analytics Endpoints
```bash
echo "Testing Analytics Endpoints..."

# Dashboard
curl -sf http://localhost:8000/api/analytics/dashboard && echo "✅ dashboard" || echo "❌ dashboard"

# Summary
curl -sf http://localhost:8000/api/analytics/summary && echo "✅ summary" || echo "❌ summary"

# Monthly
curl -sf http://localhost:8000/api/analytics/monthly && echo "✅ monthly" || echo "❌ monthly"

# Category monthly
curl -sf http://localhost:8000/api/analytics/category-monthly && echo "✅ category-monthly" || echo "❌ category-monthly"

# Cashflow
curl -sf http://localhost:8000/api/analytics/cashflow && echo "✅ cashflow" || echo "❌ cashflow"

# Predictions
curl -sf http://localhost:8000/api/analytics/predictions && echo "✅ predictions" || echo "❌ predictions"

# Merchants
curl -sf http://localhost:8000/api/analytics/merchants && echo "✅ merchants" || echo "❌ merchants"

# Predictive insights
curl -sf http://localhost:8000/api/analytics/predictive/insights && echo "✅ predictive/insights" || echo "❌ predictive/insights"

# AI analytics
curl -sf http://localhost:8000/api/analytics/ai/dashboard-summary && echo "✅ ai/dashboard-summary" || echo "❌ ai/dashboard-summary"
```

### 6.2 Verify Analytics Have Data
```bash
# Dashboard should have real numbers
curl -s http://localhost:8000/api/analytics/dashboard | jq '{
  total_income: .total_income,
  total_expenses: .total_expenses,
  transaction_count: .transaction_count
}'

# Monthly should have multiple months
curl -s http://localhost:8000/api/analytics/monthly | jq 'length'
```

### 6.3 Debug Analytics Issues

**Issue: Analytics return empty/zeros**
```bash
# Check if data exists
curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total'

# Check analytics calculation
cat apps/backend/src/ledgerloop/core/analytics*.py | head -100

# Check for date range issues
curl -s "http://localhost:8000/api/analytics/dashboard?start_date=2024-01-01&end_date=2025-12-31" | jq .
```

---

## PHASE 7: FULL SYSTEM VERIFICATION

### 7.1 Data Integrity Check
```bash
echo "📊 Data Integrity Report"
echo "========================"

# Total transactions
TOTAL=$(curl -s "http://localhost:8000/api/transactions?limit=1" | jq '.meta.total // .total // 0')
echo "Total Transactions: $TOTAL"

# Categorized
CATEGORIZED=$(curl -s "http://localhost:8000/api/transactions?has_category=true&limit=1" | jq '.meta.total // .total // 0')
echo "Categorized: $CATEGORIZED"

# Uncategorized
UNCATEGORIZED=$(curl -s "http://localhost:8000/api/transactions?has_category=false&limit=1" | jq '.meta.total // .total // 0')
echo "Uncategorized: $UNCATEGORIZED"

# Categories
CATEGORIES=$(curl -s http://localhost:8000/api/categories | jq 'length')
echo "Categories: $CATEGORIES"

# Rules
RULES=$(curl -s http://localhost:8000/api/rules | jq 'length')
echo "Rules: $RULES"

# Recurring
RECURRING=$(curl -s http://localhost:8000/api/recurring | jq 'length')
echo "Recurring Detected: $RECURRING"

# Transfers
TRANSFERS=$(curl -s http://localhost:8000/api/transfers | jq 'length')
echo "Transfer Pairs: $TRANSFERS"

# Import runs
IMPORTS=$(curl -s http://localhost:8000/api/import/runs | jq 'length')
echo "Import Runs: $IMPORTS"
```

### 7.2 Frontend Verification
```bash
echo "🖥️ Frontend Page Check"
echo "======================"

for page in "/" "/transactions" "/categories" "/rules" "/recurring" "/transfers" "/ai" "/ingest" "/export" "/settings" "/audit"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000$page")
    if [ "$status" == "200" ]; then
        echo "✅ $page"
    else
        echo "❌ $page (HTTP $status)"
    fi
done
```

### 7.3 Check for Console Errors
Open browser at `http://localhost:3000` and check DevTools Console for each page:
- Dashboard
- Transactions
- Categories
- Analytics

---

## PHASE 8: ROOT CAUSE FIXES

As you encounter issues, document and fix them using this framework:

### Issue Template
```markdown
## ISSUE: [Brief Description]

**Symptom:** What you observed
**Location:** File and line number
**Root Cause:** Why it's happening
**Fix:** What you changed
**Verification:** How you confirmed it's fixed
```

### Common Root Causes

**1. DuckDB SQL Incompatibility**
- Symptom: SQL errors in logs
- Root Cause: Using SQLite syntax
- Fix: Convert to DuckDB syntax (ON CONFLICT, etc.)

**2. Missing Error Handling**
- Symptom: 500 errors with no useful message
- Root Cause: Unhandled exceptions
- Fix: Add try/except with proper error responses

**3. Type Mismatches**
- Symptom: JSON serialization errors
- Root Cause: Returning incompatible types (Decimal, datetime)
- Fix: Convert to JSON-safe types before returning

**4. Missing Endpoints**
- Symptom: 404 on API calls
- Root Cause: Route not registered
- Fix: Add route to router and register in app

**5. CORS Issues**
- Symptom: Preflight failures
- Root Cause: Missing CORS headers
- Fix: Verify CORS middleware configuration

---

## OUTPUT REQUIREMENTS

### 1. `PIPELINE_RUN_LOG.md`
```markdown
# Pipeline Execution Log

## Import Pipeline
- Files Found: X
- Files Imported: X
- Transactions Created: X
- Errors: [list]
- Fixes Applied: [list]

## Categorization Pipeline
- Transactions Processed: X
- AI Categorized: X
- Rules Categorized: X
- Remaining Uncategorized: X
- Fixes Applied: [list]

## Recurring Detection
- Series Detected: X
- Monthly Total: $X
- Fixes Applied: [list]

## Transfer Detection
- Pairs Detected: X
- Pending Confirmation: X
- Fixes Applied: [list]

## Analytics Verification
- All Endpoints Working: YES/NO
- Endpoints Fixed: [list]
```

### 2. `FIXES_APPLIED.md`
```markdown
# Fixes Applied During Pipeline Execution

## Fix 1: [Title]
- **File:** path/to/file.py
- **Line:** X
- **Issue:** Description
- **Change:** What was changed
- **Verified:** How confirmed

## Fix 2: ...
```

### 3. `DATA_STATUS.md`
```markdown
# LedgerLoop Data Status

## Transaction Summary
- Total: X
- Date Range: YYYY-MM-DD to YYYY-MM-DD
- Categorized: X (Y%)
- Uncategorized: X

## Categories
- Total Categories: X
- Most Used: [list top 5]

## Recurring
- Subscriptions: X
- Monthly Total: $X

## Transfers
- Detected Pairs: X
- Confirmed: X
- Pending: X

## Data Quality
- Duplicates: X
- Missing Dates: X
- Invalid Amounts: X
```

---

## CRITICAL RULES

1. **Run pipelines with real data** - Don't just test with curl, use actual bank files
2. **Fix as you go** - Don't collect issues for later, fix them now
3. **Verify each fix** - Re-run the pipeline after fixing
4. **Document everything** - Every fix, every issue, every verification
5. **Root cause, not symptoms** - Understand WHY before fixing
6. **Keep data safe** - Don't delete transactions, backup if needed
7. **Test the full flow** - Import → Categorize → Analyze → Display

---

## BEGIN EXECUTION

Start with Phase 0. Run each pipeline. Fix issues as they arise. Leave the system fully populated and production-ready.

**Success Criteria:**
- ✅ All bank statements imported
- ✅ Transactions categorized (>80%)
- ✅ Recurring detected
- ✅ Transfers matched
- ✅ Analytics working with real data
- ✅ Zero console errors in frontend
- ✅ All pages display real data

GO.
