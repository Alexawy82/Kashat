#!/bin/bash
# LedgerLoop Health Check Script
# Usage: ./scripts/health-check.sh

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "=== LedgerLoop Health Check ==="

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected=${3:-200}

    code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$code" = "$expected" ]; then
        echo "  [OK] $name ($url) - HTTP $code"
        return 0
    else
        echo "  [FAIL] $name ($url) - HTTP $code (expected $expected)"
        return 1
    fi
}

# Track failures
FAILURES=0

echo ""
echo "Backend API Endpoints:"
check_endpoint "Health" "$BACKEND_URL/api/health" || ((FAILURES++))
check_endpoint "Transactions" "$BACKEND_URL/api/transactions?limit=1" || ((FAILURES++))
check_endpoint "Categories" "$BACKEND_URL/api/categories" || ((FAILURES++))
check_endpoint "Rules" "$BACKEND_URL/api/rules" || ((FAILURES++))
check_endpoint "Analytics" "$BACKEND_URL/api/analytics/dashboard" || ((FAILURES++))
check_endpoint "Settings" "$BACKEND_URL/api/settings" || ((FAILURES++))

echo ""
echo "Frontend Pages:"
check_endpoint "Dashboard" "$FRONTEND_URL/" || ((FAILURES++))
check_endpoint "Transactions" "$FRONTEND_URL/transactions" || ((FAILURES++))
check_endpoint "Categories" "$FRONTEND_URL/categories" || ((FAILURES++))
check_endpoint "Settings" "$FRONTEND_URL/settings" || ((FAILURES++))

echo ""
echo "Docker Container Status:"
docker ps --filter "name=kashat" --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  (docker not available)"

echo ""
if [ $FAILURES -eq 0 ]; then
    echo "=== All Health Checks Passed ==="
    exit 0
else
    echo "=== $FAILURES Health Check(s) Failed ==="
    exit 1
fi
