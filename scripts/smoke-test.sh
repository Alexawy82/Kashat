#!/bin/bash
# LedgerLoop Complete Smoke Test
# Usage: ./scripts/smoke-test.sh

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "=============================================="
echo "       LedgerLoop Complete Smoke Test        "
echo "=============================================="
echo ""

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name=$1
    local method=$2
    local url=$3
    local expected=${4:-200}

    code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" 2>/dev/null || echo "000")

    if [ "$code" = "$expected" ]; then
        echo "[PASS] $name"
        ((PASSED++))
    else
        echo "[FAIL] $name (got $code, expected $expected)"
        ((FAILED++))
    fi
}

echo "=== Backend API Tests ==="
test_endpoint "GET /api/health" GET "$BACKEND_URL/api/health"
test_endpoint "GET /api/transactions" GET "$BACKEND_URL/api/transactions?limit=1"
test_endpoint "GET /api/categories" GET "$BACKEND_URL/api/categories"
test_endpoint "GET /api/rules" GET "$BACKEND_URL/api/rules"
test_endpoint "GET /api/recurring" GET "$BACKEND_URL/api/recurring"
test_endpoint "GET /api/transfers" GET "$BACKEND_URL/api/transfers"
test_endpoint "GET /api/accounts" GET "$BACKEND_URL/api/accounts"
test_endpoint "GET /api/settings" GET "$BACKEND_URL/api/settings"
test_endpoint "GET /api/analytics/dashboard" GET "$BACKEND_URL/api/analytics/dashboard"
test_endpoint "GET /api/analytics/summary" GET "$BACKEND_URL/api/analytics/summary"
test_endpoint "GET /api/imports/runs" GET "$BACKEND_URL/api/imports/runs"

echo ""
echo "=== Frontend Page Tests ==="
test_endpoint "GET /" GET "$FRONTEND_URL/"
test_endpoint "GET /transactions" GET "$FRONTEND_URL/transactions"
test_endpoint "GET /categories" GET "$FRONTEND_URL/categories"
test_endpoint "GET /rules" GET "$FRONTEND_URL/rules"
test_endpoint "GET /recurring" GET "$FRONTEND_URL/recurring"
test_endpoint "GET /transfers" GET "$FRONTEND_URL/transfers"
test_endpoint "GET /ai" GET "$FRONTEND_URL/ai"
test_endpoint "GET /ingest" GET "$FRONTEND_URL/ingest"
test_endpoint "GET /export" GET "$FRONTEND_URL/export"
test_endpoint "GET /settings" GET "$FRONTEND_URL/settings"
test_endpoint "GET /audit" GET "$FRONTEND_URL/audit"
test_endpoint "GET /live" GET "$FRONTEND_URL/live"
test_endpoint "GET /metrics" GET "$FRONTEND_URL/metrics"
test_endpoint "GET /status" GET "$FRONTEND_URL/status"

echo ""
echo "=============================================="
echo "            Test Summary                      "
echo "=============================================="
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo "  Total:  $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "ALL TESTS PASSED!"
    exit 0
else
    echo "SOME TESTS FAILED"
    exit 1
fi
