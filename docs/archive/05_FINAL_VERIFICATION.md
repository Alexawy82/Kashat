# Phase 5: Final Verification & Testing

## Your Role
You are a QA lead performing final verification before production release.

## Context
All previous phases should be complete:
- ✅ Phase 1: Backend fixes
- ✅ Phase 2: Frontend fixes
- ✅ Phase 3: API verification
- ✅ Phase 4: CoreLab deployment config

Now verify EVERYTHING works end-to-end.

## Verification Checklist

### 1. Build Verification

```bash
# Backend - verify no import errors
cd apps/backend
python -c "from ledgerloop.api import create_app; app = create_app(); print('✅ Backend imports OK')"

# Frontend - verify builds without errors
cd apps/web
npm run build
echo "✅ Frontend builds OK"

# Docker - verify images build
cd ../..
docker-compose build --no-cache
echo "✅ Docker images build OK"
```

### 2. Startup Verification

```bash
# Start services
docker-compose up -d

# Wait for health
sleep 15

# Check containers are running
docker ps | grep ledgerloop
```

### 3. API Endpoint Smoke Tests

Test EVERY endpoint returns valid response (not 500, not 404):

```bash
#!/bin/bash
# Save as scripts/smoke-test-api.sh

BASE_URL="http://localhost:8000"
FAILED=0

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected=$3
    
    status=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint")
    
    if [ "$status" == "$expected" ]; then
        echo "✅ $method $endpoint -> $status"
    else
        echo "❌ $method $endpoint -> $status (expected $expected)"
        FAILED=$((FAILED+1))
    fi
}

echo "🧪 API Smoke Tests"
echo "=================="

# Health
test_endpoint GET "/api/health" 200
test_endpoint GET "/api/health/live" 200
test_endpoint GET "/api/health/ready" 200
test_endpoint GET "/api/health/detailed" 200

# Transactions
test_endpoint GET "/api/transactions" 200
test_endpoint GET "/api/transactions?limit=5" 200

# Categories
test_endpoint GET "/api/categories" 200
test_endpoint GET "/api/categories/tree" 200

# Rules
test_endpoint GET "/api/rules" 200
test_endpoint GET "/api/rules/suggestions" 200

# Recurring
test_endpoint GET "/api/recurring" 200
test_endpoint GET "/api/recurring/series" 200

# Transfers
test_endpoint GET "/api/transfers" 200

# Analytics
test_endpoint GET "/api/analytics/dashboard" 200
test_endpoint GET "/api/analytics/summary" 200
test_endpoint GET "/api/analytics/monthly" 200
test_endpoint GET "/api/analytics/category-monthly" 200
test_endpoint GET "/api/analytics/cashflow" 200
test_endpoint GET "/api/analytics/predictions" 200
test_endpoint GET "/api/analytics/merchants" 200

# AI
test_endpoint GET "/api/ai/stats" 200
test_endpoint GET "/api/ai/status" 200
test_endpoint GET "/api/ai/categories" 200
test_endpoint GET "/api/ai/merchant-memory/stats" 200

# Predictive Analytics
test_endpoint GET "/api/analytics/predictive/insights" 200
test_endpoint GET "/api/analytics/predictive/patterns" 200
test_endpoint GET "/api/analytics/predictive/cashflow-forecast" 200

# AI Analytics
test_endpoint GET "/api/analytics/ai/dashboard-summary" 200
test_endpoint GET "/api/analytics/ai/trends" 200
test_endpoint GET "/api/analytics/ai/spending-patterns" 200

# Import/Export
test_endpoint GET "/api/import/runs" 200
test_endpoint GET "/api/imports/runs" 200

# Accounts
test_endpoint GET "/api/accounts" 200

# Audit
test_endpoint GET "/api/audit/logs" 200

# Settings
test_endpoint GET "/api/settings" 200

# Metrics
test_endpoint GET "/metrics" 200

echo ""
if [ $FAILED -eq 0 ]; then
    echo "✅ All API tests passed!"
else
    echo "❌ $FAILED tests failed"
    exit 1
fi
```

### 4. Frontend Page Tests

Test EVERY page loads without JavaScript errors:

```bash
#!/bin/bash
# Save as scripts/smoke-test-pages.sh

BASE_URL="http://localhost:3000"
FAILED=0

test_page() {
    local path=$1
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$path")
    
    if [ "$status" == "200" ]; then
        echo "✅ $path -> $status"
    else
        echo "❌ $path -> $status"
        FAILED=$((FAILED+1))
    fi
}

echo "🧪 Frontend Page Tests"
echo "======================"

test_page "/"
test_page "/transactions"
test_page "/categories"
test_page "/rules"
test_page "/recurring"
test_page "/transfers"
test_page "/ai"
test_page "/ingest"
test_page "/export"
test_page "/settings"
test_page "/settings/data-management"
test_page "/audit"
test_page "/metrics"
test_page "/status"
test_page "/live"

echo ""
if [ $FAILED -eq 0 ]; then
    echo "✅ All page tests passed!"
else
    echo "❌ $FAILED pages failed"
    exit 1
fi
```

### 5. Browser Console Check

Manually open each page in browser and check DevTools Console for:
- ❌ No red errors
- ❌ No failed network requests
- ⚠️ Warnings are OK (but note them)

Pages to check:
1. Dashboard (`/`)
2. Transactions (`/transactions`)
3. Categories (`/categories`)
4. Rules (`/rules`)
5. Recurring (`/recurring`)
6. Transfers (`/transfers`)
7. AI (`/ai`)
8. Import (`/ingest`)
9. Export (`/export`)
10. Settings (`/settings`)
11. Audit (`/audit`)

### 6. Feature Functionality Tests

Test each feature actually WORKS:

**Transactions:**
- [ ] List loads with data
- [ ] Can filter by date
- [ ] Can filter by category
- [ ] Can search
- [ ] Pagination works

**Categories:**
- [ ] Tree view loads
- [ ] Can create category
- [ ] Can edit category
- [ ] Can delete category (if no transactions)
- [ ] Can assign to transaction

**Rules:**
- [ ] List loads
- [ ] Can create rule
- [ ] Can edit rule
- [ ] Can delete rule
- [ ] Suggestions show

**Recurring:**
- [ ] Subscriptions detected
- [ ] Can confirm/reject
- [ ] Monthly totals show

**Transfers:**
- [ ] Pairs detected
- [ ] Can confirm/reject
- [ ] Status filter works

**Analytics:**
- [ ] Dashboard charts render
- [ ] Monthly trends show
- [ ] Category breakdown shows
- [ ] Date range selector works

**Import:**
- [ ] File upload works
- [ ] Processing completes
- [ ] Transactions appear

**Export:**
- [ ] CSV download works
- [ ] Data is correct

**Settings:**
- [ ] Settings load
- [ ] Can modify settings
- [ ] Changes persist

### 7. Data Integrity Check

```bash
# Check database has data
curl -s http://localhost:8000/api/transactions?limit=1 | jq '.data | length'
# Should be >= 1

curl -s http://localhost:8000/api/categories | jq '. | length'
# Should be >= 1

curl -s http://localhost:8000/api/analytics/summary | jq '.total_transactions'
# Should match actual count
```

### 8. Performance Check

```bash
# API response times should be < 500ms
time curl -s http://localhost:8000/api/transactions?limit=100 > /dev/null
time curl -s http://localhost:8000/api/analytics/dashboard > /dev/null
time curl -s http://localhost:8000/api/categories/tree > /dev/null
```

### 9. Error Handling Check

Test error cases:
```bash
# 404 for missing resource
curl -s http://localhost:8000/api/transactions/999999 | jq '.error'

# Invalid query params
curl -s "http://localhost:8000/api/transactions?limit=invalid" | jq '.error'

# Invalid POST body
curl -s -X POST http://localhost:8000/api/categories \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}' | jq '.error'
```

### 10. Docker Stability Check

```bash
# Check containers stay healthy after 5 minutes
docker-compose up -d
sleep 300
docker ps | grep ledgerloop

# Both should show "healthy" or "Up X minutes"
```

## Output Required

### Create `scripts/smoke-test.sh`

Combined smoke test script that runs all tests:

```bash
#!/bin/bash
set -e

echo "🧪 LedgerLoop Smoke Tests"
echo "========================="
echo ""

./scripts/smoke-test-api.sh
./scripts/smoke-test-pages.sh

echo ""
echo "✅ All smoke tests passed!"
echo "🚀 Ready for production deployment"
```

### Create `VERIFICATION_REPORT.md`

```markdown
# LedgerLoop Verification Report

**Date:** [DATE]
**Tester:** Claude

## Build Status
- [ ] Backend imports: PASS/FAIL
- [ ] Frontend build: PASS/FAIL
- [ ] Docker build: PASS/FAIL

## API Tests
[Results from smoke-test-api.sh]

## Page Tests
[Results from smoke-test-pages.sh]

## Feature Tests
[Checklist results]

## Browser Console
[Any errors found]

## Performance
[Response time measurements]

## Issues Found
[List any remaining issues]

## Conclusion
[Ready / Not Ready for production]
```

### Create `RELEASE_CHECKLIST.md`

```markdown
# LedgerLoop Release Checklist

## Pre-Deployment
- [ ] All smoke tests pass
- [ ] No console errors in browser
- [ ] Docker images build successfully
- [ ] Environment variables configured

## Deployment
- [ ] Run deploy-corelab.sh
- [ ] Verify health checks pass
- [ ] Create initial backup

## Post-Deployment
- [ ] Verify all pages accessible
- [ ] Verify data is correct
- [ ] Test one transaction edit
- [ ] Test one category create

## Monitoring
- [ ] Set up backup cron job
- [ ] Bookmark health check URL
```

## Rules
- ALL tests must pass before declaring production-ready
- Document any skipped tests with reason
- Any failing test = NOT ready for production
- Create all output files even if tests fail
