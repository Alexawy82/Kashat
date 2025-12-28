# Phase 3: API Integration Verification

## Your Role
You are a QA engineer verifying that frontend and backend APIs are perfectly aligned.

## Context
- Backend: `http://localhost:8000/api/`
- Frontend: `apps/web/src/`
- Both should be running in Docker

## Verification Tasks

### 1. Extract All Frontend API Calls

Find every API call the frontend makes:

```bash
grep -rn "fetch\|apiRequest\|axios\|/api/" apps/web/src/ | grep -v node_modules
```

Create a list of all endpoints the frontend expects:
```
GET  /api/transactions
GET  /api/transactions/:id
POST /api/transactions
PUT  /api/transactions/:id
DELETE /api/transactions/:id
... etc
```

### 2. Extract All Backend Endpoints

List all registered routes:

```bash
grep -rn "@router\.\|@app\." apps/backend/src/ledgerloop/api/
```

Or check the OpenAPI spec:
```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys'
```

### 3. Cross-Reference

Create a matrix:

| Frontend Expects | Backend Has | Status |
|-----------------|-------------|--------|
| GET /api/transactions | ✅ | OK |
| GET /api/analytics/foo | ❌ | MISSING |
| ... | ... | ... |

### 4. Test Each Endpoint

For each endpoint, verify it works:

```bash
# Health check
curl http://localhost:8000/api/health

# Transactions
curl http://localhost:8000/api/transactions?limit=5
curl http://localhost:8000/api/transactions/1

# Categories
curl http://localhost:8000/api/categories
curl http://localhost:8000/api/categories/tree

# Rules
curl http://localhost:8000/api/rules
curl http://localhost:8000/api/rules/suggestions

# Recurring
curl http://localhost:8000/api/recurring
curl http://localhost:8000/api/recurring/series

# Transfers
curl http://localhost:8000/api/transfers
curl http://localhost:8000/api/transfers?status=pending

# Analytics
curl http://localhost:8000/api/analytics/dashboard
curl http://localhost:8000/api/analytics/summary
curl http://localhost:8000/api/analytics/monthly
curl http://localhost:8000/api/analytics/category-monthly
curl http://localhost:8000/api/analytics/predictions
curl http://localhost:8000/api/analytics/cashflow
curl http://localhost:8000/api/analytics/merchants

# AI
curl http://localhost:8000/api/ai/stats
curl http://localhost:8000/api/ai/status
curl http://localhost:8000/api/ai/categories

# Import/Ingest
curl http://localhost:8000/api/import/runs
curl http://localhost:8000/api/imports/runs

# Export
curl http://localhost:8000/api/export/csv

# Accounts
curl http://localhost:8000/api/accounts

# Audit
curl http://localhost:8000/api/audit/logs?limit=10

# Settings
curl http://localhost:8000/api/settings

# Predictive Analytics
curl http://localhost:8000/api/analytics/predictive/insights
curl http://localhost:8000/api/analytics/predictive/patterns
curl http://localhost:8000/api/analytics/predictive/cashflow-forecast

# AI Analytics
curl http://localhost:8000/api/analytics/ai/dashboard-summary
curl http://localhost:8000/api/analytics/ai/trends
curl http://localhost:8000/api/analytics/ai/spending-patterns

# Merchant Memory
curl http://localhost:8000/api/ai/merchant-memory/stats
```

### 5. Check Response Shapes

For each endpoint, verify the response shape matches what frontend expects:

**Frontend expects (example):**
```typescript
interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  category_id?: string;
  // ...
}
```

**Backend returns:**
```json
{
  "id": "123",
  "date": "2025-01-15",
  "description": "AMAZON",
  "amount": -45.99,
  "category_id": null
}
```

Check for mismatches:
- Field names (snake_case vs camelCase)
- Data types (string vs number)
- Null handling
- Date formats

### 6. Fix Mismatches

**Option A: Fix Backend Response**
```python
# In the route handler
return {
    "id": str(transaction.id),
    "date": transaction.date.isoformat(),
    ...
}
```

**Option B: Fix Frontend Types**
```typescript
// In the type definition
interface Transaction {
  id: number;  // was string
  ...
}
```

**Option C: Add Transformation Layer**
```typescript
// In api.ts
const transformTransaction = (raw: any): Transaction => ({
  id: String(raw.id),
  date: raw.date,
  ...
});
```

### 7. Handle Missing Endpoints

If frontend calls an endpoint that doesn't exist:

**Option A: Create the endpoint**
```python
@router.get("/missing-endpoint")
def missing_endpoint():
    return {"data": []}
```

**Option B: Remove frontend call**
```typescript
// Delete the API call and any UI that depends on it
```

**Option C: Return mock/empty data**
```python
@router.get("/not-implemented")
def not_implemented():
    return {"data": [], "message": "Feature not available"}
```

### 8. Test CORS

Verify CORS works for all endpoints:

```bash
curl -X OPTIONS http://localhost:8000/api/transactions \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

Should return:
- `access-control-allow-origin: http://localhost:3000`
- `access-control-allow-methods: GET, POST, ...`

## Output Required

Create `API_VERIFICATION_REPORT.md`:

```markdown
# API Verification Report

## Endpoint Status

| Endpoint | Method | Frontend Uses | Backend Has | Response OK | Notes |
|----------|--------|---------------|-------------|-------------|-------|
| /api/transactions | GET | ✅ | ✅ | ✅ | |
| /api/foo/bar | GET | ✅ | ❌ | N/A | MISSING - needs creation |

## Fixes Applied
- Created endpoint X
- Fixed response shape for Y
- Removed frontend call to Z

## Remaining Issues
- None (or list them)
```

## Rules
- Every frontend API call MUST have a working backend endpoint
- Response shapes MUST match frontend expectations
- All endpoints MUST return proper JSON (not HTML errors)
- All endpoints MUST handle errors gracefully
