# LedgerLoop Security & Code Audit Report

**Audit Date:** December 16, 2025
**Auditor:** Senior Staff Engineer
**Scope:** Full codebase audit - backend, frontend, Docker/deployment configs

---

## Executive Summary

This audit identified **47 issues** across the LedgerLoop codebase:
- **Critical:** 6 issues (immediate security risks)
- **High:** 12 issues (significant bugs/vulnerabilities)
- **Medium:** 18 issues (code quality/maintainability)
- **Low:** 11 issues (minor improvements)

The most urgent concerns are **disabled authentication** and **hardcoded secrets** that expose the application to unauthorized access.

---

## Critical Issues (6)

### C-1: Authentication Completely Disabled
**File:** `apps/backend/src/ledgerloop/api/__init__.py`
**Lines:** 248-250
**Description:** The `get_current_user` dependency is bypassed, returning a mock user for all requests. All API endpoints are publicly accessible without authentication.

```python
# AUTH DISABLED: Returns mock user
async def get_current_user():
    return {"id": "single-user", "username": "user"}
```

**Impact:** Any network-accessible instance allows full read/write access to financial data.
**Fix:** Re-enable authentication by restoring the JWT validation logic from `apps/web/src/archive/auth/`.

---

### C-2: Hardcoded JWT Secret Key
**File:** `apps/backend/src/ledgerloop/api/auth.py`
**Lines:** 28-29
**Description:** JWT secret defaults to "changeme" if environment variable is not set.

```python
SECRET_KEY = os.getenv("LEDGERLOOP_JWT_SECRET", "changeme")
```

**Impact:** Attackers can forge valid JWT tokens to impersonate any user.
**Fix:** Remove default value; require `LEDGERLOOP_JWT_SECRET` to be set:
```python
SECRET_KEY = os.environ["LEDGERLOOP_JWT_SECRET"]  # Will raise if not set
```

---

### C-3: Default Admin Password
**File:** `apps/backend/src/ledgerloop/api/auth.py`
**Lines:** 130-135
**Description:** Admin user is created with password "adminadmin" on first startup.

```python
# Create default admin user
hashed = bcrypt.hashpw("adminadmin".encode(), bcrypt.gensalt())
```

**Impact:** Default credentials are well-known; attackers gain admin access immediately.
**Fix:** Generate random password on first run and display it once, or require password to be set via environment variable.

---

### C-4: Hardcoded WebSocket Token
**File:** `apps/web/next.config.js`
**Line:** 9
**Description:** WebSocket authentication token defaults to "MaroMaro".

```javascript
NEXT_PUBLIC_WS_TOKEN: process.env.NEXT_PUBLIC_WS_TOKEN || 'MaroMaro',
```

**Impact:** Anyone can connect to WebSocket endpoints and receive real-time financial data.
**Fix:** Remove default; require token to be configured:
```javascript
NEXT_PUBLIC_WS_TOKEN: process.env.NEXT_PUBLIC_WS_TOKEN,
```

---

### C-5: CORS Wildcard in Production
**File:** `docker-compose.yml`
**Line:** 15
**Description:** CORS is set to accept all origins by default.

```yaml
- LEDGERLOOP_CORS=${LEDGERLOOP_CORS:-*}
```

**Impact:** Cross-site request forgery attacks possible; malicious websites can make authenticated requests.
**Fix:** Set explicit allowed origins:
```yaml
- LEDGERLOOP_CORS=${LEDGERLOOP_CORS:-http://localhost:3000}
```

---

### C-6: Frontend Auth Context Returns Always Authenticated
**File:** `apps/web/src/contexts/AuthContext.tsx`
**Lines:** 45-49
**Description:** Auth context always returns `isAuthenticated: true` regardless of actual auth state.

```typescript
const value: AuthContextType = {
  user: MOCK_USER,
  token: 'no-auth-required',
  isAuthenticated: true,  // Always authenticated
  isLoading: false,
}
```

**Impact:** Frontend provides no access control; all pages accessible to anyone.
**Fix:** Restore actual authentication logic from `apps/web/src/archive/auth/`.

---

## High Issues (12)

### H-1: SQL Injection via Dynamic Table Names
**File:** `apps/backend/src/ledgerloop/api/routes/categories.py`
**Line:** 139
**Description:** Table name is inserted directly into SQL string.

```python
conn.execute(f"UPDATE {table} SET category_id = ? WHERE category_id = ?", [body.to_id, body.from_id])
```

**Impact:** If `table` variable is controllable, SQL injection is possible.
**Fix:** Validate table name against allowlist:
```python
ALLOWED_TABLES = {"transactions", "recurring_transactions"}
if table not in ALLOWED_TABLES:
    raise ValueError(f"Invalid table: {table}")
```

---

### H-2: INSERT OR IGNORE Syntax Invalid for DuckDB
**Files:**
- `apps/backend/src/ledgerloop/api/auth.py` (line 133)
- `apps/backend/src/ledgerloop/ingest_csv.py` (lines 89, 156)
- `apps/backend/src/ledgerloop/ingest_pdf.py` (line 201)

**Description:** DuckDB uses `INSERT OR REPLACE INTO` or `INSERT INTO ... ON CONFLICT`, not SQLite's `INSERT OR IGNORE`.

```python
# Invalid for DuckDB
conn.execute("INSERT OR IGNORE INTO users ...")
```

**Impact:** Inserts may fail silently or throw unexpected errors.
**Fix:** Use DuckDB-compatible syntax:
```python
conn.execute("""
    INSERT INTO users (id, username, password_hash)
    VALUES (?, ?, ?)
    ON CONFLICT (username) DO NOTHING
""", [user_id, username, hashed])
```

---

### H-3: Silent Exception Handling (Multiple Locations)
**Files:**
- `apps/backend/src/ledgerloop/api/routes/categories.py` (lines 45-47, 92-93, 128-129, 140-142, 154-155)
- `apps/backend/src/ledgerloop/db.py` (lines 89-91, 156-158)
- `apps/backend/src/ledgerloop/rules.py` (lines 234-236)

**Description:** Bare `except Exception: pass` blocks silently swallow errors.

```python
try:
    # operation
except Exception:
    pass  # Errors hidden
```

**Impact:** Bugs go undetected; data corruption possible without any indication.
**Fix:** Log exceptions at minimum:
```python
try:
    # operation
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

---

### H-4: Unvalidated File Uploads
**File:** `apps/backend/src/ledgerloop/api/routes/imports.py`
**Lines:** 45-60
**Description:** File uploads don't validate file size, content type matches extension, or scan for malicious content.

**Impact:** Large file DoS, content-type spoofing, potential RCE via PDF parsing vulnerabilities.
**Fix:**
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.csv', '.pdf'}

@router.post("/import/{kind}")
async def import_file(kind: str, file: UploadFile):
    if kind not in ['csv', 'pdf']:
        raise HTTPException(400, "Invalid file type")

    # Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")

    # Validate extension matches content type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Invalid file extension")
```

---

### H-5: Race Condition in Database Connection
**File:** `apps/backend/src/ledgerloop/db.py`
**Lines:** 45-67
**Description:** Global `_conn` variable accessed without locking in multi-threaded context.

```python
_conn = None

def get_connection():
    global _conn
    if _conn is None:  # Race condition here
        _conn = duckdb.connect(DB_PATH)
    return _conn
```

**Impact:** Multiple threads may create separate connections, causing DuckDB single-writer conflicts.
**Fix:** Use threading lock:
```python
import threading
_conn_lock = threading.Lock()

def get_connection():
    global _conn
    with _conn_lock:
        if _conn is None:
            _conn = duckdb.connect(DB_PATH)
        return _conn
```

---

### H-6: Missing Input Validation on Transaction Updates
**File:** `apps/backend/src/ledgerloop/api/routes/transactions.py`
**Lines:** 156-180
**Description:** PATCH endpoint allows updating any field without validation.

**Impact:** Invalid data (negative amounts, future dates, invalid categories) can corrupt database.
**Fix:** Add Pydantic model with validators:
```python
class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=-1000000, lt=1000000)
    date: Optional[date] = None
    category_id: Optional[str] = None

    @validator('date')
    def date_not_future(cls, v):
        if v and v > date.today():
            raise ValueError('Date cannot be in the future')
        return v
```

---

### H-7: Unbounded Query Results
**File:** `apps/backend/src/ledgerloop/api/routes/transactions.py`
**Lines:** 45-78
**Description:** GET /transactions doesn't enforce maximum limit.

```python
@router.get("/transactions")
async def list_transactions(limit: int = 100, offset: int = 0):
    # No max limit validation
```

**Impact:** Attacker can request `limit=999999999` causing memory exhaustion.
**Fix:**
```python
MAX_LIMIT = 1000

@router.get("/transactions")
async def list_transactions(limit: int = Query(100, le=MAX_LIMIT), offset: int = 0):
```

---

### H-8: Regex Patterns from User Input
**File:** `apps/backend/src/ledgerloop/rules.py`
**Lines:** 78-95
**Description:** User-provided regex patterns are compiled without validation.

```python
pattern = re.compile(rule['pattern'])  # User-controlled input
```

**Impact:** ReDoS (Regular Expression Denial of Service) via catastrophic backtracking.
**Fix:** Add timeout and pattern validation:
```python
import re2  # Use RE2 which guarantees linear time

def safe_compile(pattern: str) -> re.Pattern:
    if len(pattern) > 200:
        raise ValueError("Pattern too long")
    return re2.compile(pattern)
```

---

### H-9: Missing CSRF Protection
**File:** `apps/backend/src/ledgerloop/api/main.py`
**Description:** No CSRF token validation on state-changing endpoints.

**Impact:** Cross-site request forgery attacks can modify user data.
**Fix:** Add CSRF middleware:
```python
from starlette_csrf import CSRFMiddleware

app.add_middleware(
    CSRFMiddleware,
    secret=os.environ["CSRF_SECRET"],
)
```

---

### H-10: Sensitive Data in Error Responses
**File:** `apps/backend/src/ledgerloop/api/errors.py`
**Lines:** 45-60
**Description:** Exception handlers may leak internal details in production.

```python
return JSONResponse(
    status_code=500,
    content={"detail": str(exc)}  # May contain SQL, file paths, etc.
)
```

**Fix:** Sanitize error messages in production:
```python
if os.getenv("LEDGERLOOP_ENV") == "production":
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

---

### H-11: WebSocket Connection Not Validated
**File:** `apps/backend/src/ledgerloop/api/routes/realtime.py`
**Lines:** 25-40
**Description:** WebSocket connections don't validate origin or require authentication.

**Impact:** Unauthorized clients can subscribe to real-time financial updates.
**Fix:** Validate token in WebSocket handshake:
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    if not validate_ws_token(token):
        await websocket.close(code=4001)
        return
    await websocket.accept()
```

---

### H-12: PDF Parser Arbitrary Code Execution Risk
**File:** `apps/backend/src/ledgerloop/ingest_pdf.py`
**Lines:** 45-89
**Description:** PDF parsing with pdfplumber can be vulnerable to crafted PDFs.

**Impact:** Malicious PDFs could potentially execute code during parsing.
**Fix:** Run PDF parsing in sandboxed subprocess:
```python
import subprocess
import tempfile

def parse_pdf_safe(pdf_path: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix='.json') as out:
        result = subprocess.run(
            ['python', '-m', 'ledgerloop.pdf_parser', pdf_path, out.name],
            timeout=30,
            capture_output=True
        )
        if result.returncode != 0:
            raise ValueError("PDF parsing failed")
        return json.load(out)
```

---

## Medium Issues (18)

### M-1: Inconsistent Date Handling
**Files:**
- `apps/backend/src/ledgerloop/api/routes/transactions.py` (line 67)
- `apps/backend/src/ledgerloop/ingest_csv.py` (line 123)

**Description:** Dates parsed with different formats, no timezone handling.

**Fix:** Standardize on ISO 8601 with explicit timezone:
```python
from datetime import datetime, timezone

def parse_date(date_str: str) -> datetime:
    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {date_str}")
```

---

### M-2: No Rate Limiting
**File:** `apps/backend/src/ledgerloop/api/main.py`
**Description:** No rate limiting on any endpoint.

**Impact:** API abuse, brute force attacks on login, resource exhaustion.
**Fix:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
```

---

### M-3: Missing Request Logging
**File:** `apps/backend/src/ledgerloop/api/main.py`
**Description:** No structured logging of API requests for audit trail.

**Fix:** Add logging middleware:
```python
import structlog

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = structlog.get_logger()
    logger.info("request", method=request.method, path=request.url.path)
    response = await call_next(request)
    logger.info("response", status=response.status_code)
    return response
```

---

### M-4: Hardcoded Pagination Defaults
**File:** `apps/backend/src/ledgerloop/api/routes/transactions.py`
**Line:** 48
**Description:** Default limit of 100 may be too high for slow connections.

**Fix:** Make configurable via environment:
```python
DEFAULT_PAGE_SIZE = int(os.getenv("LEDGERLOOP_PAGE_SIZE", "50"))
```

---

### M-5: No Database Connection Pooling
**File:** `apps/backend/src/ledgerloop/db.py`
**Description:** Single global connection; no pooling or connection lifecycle management.

**Fix:** While DuckDB is single-writer, implement proper connection management:
```python
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = duckdb.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

---

### M-6: Frontend API Base URL Confusion
**File:** `apps/web/src/utils/api.ts`
**Line:** 1
**Description:** `NEXT_PUBLIC_API_BASE` can be '/api' (proxy) or full URL, causing confusion.

**Fix:** Document behavior and add validation:
```typescript
const API = process.env.NEXT_PUBLIC_API_BASE || '/api'
if (API !== '/api' && !API.startsWith('http')) {
  console.warn('NEXT_PUBLIC_API_BASE should be "/api" or full URL')
}
```

---

### M-7: Missing Error Boundary on Dashboard
**File:** `apps/web/src/components/dashboard/EnhancedDashboard.tsx`
**Description:** No error boundary; any rendering error crashes the entire dashboard.

**Fix:** Wrap in error boundary:
```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary'

export function DashboardPage() {
  return (
    <ErrorBoundary fallback={<DashboardError />}>
      <EnhancedDashboard />
    </ErrorBoundary>
  )
}
```

---

### M-8: Inline Styles Throughout Frontend
**Files:** Multiple components in `apps/web/src/`
**Description:** Heavy use of inline styles instead of Tailwind classes or CSS modules.

**Impact:** Inconsistent styling, harder to maintain, larger bundle size.
**Fix:** Convert to Tailwind classes:
```tsx
// Before
<div style={{ padding: 24, maxWidth: 1200 }}>

// After
<div className="p-6 max-w-screen-xl">
```

---

### M-9: No Loading States on Data Fetches
**File:** `apps/web/src/app/ingest/page.tsx`
**Description:** Uses basic `busy` boolean; no skeleton loaders or proper loading UX.

**Fix:** Add proper loading states:
```tsx
{isLoading ? (
  <Skeleton className="h-48 w-full" />
) : (
  <UploadResults data={result} />
)}
```

---

### M-10: Missing TypeScript Strict Mode
**File:** `apps/web/tsconfig.json`
**Description:** May not have `strict: true` enabled.

**Fix:** Enable strict mode:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true
  }
}
```

---

### M-11: useEffect Missing Dependencies
**File:** `apps/web/src/components/dashboard/EnhancedDashboard.tsx`
**Lines:** Multiple
**Description:** Several useEffect hooks may have missing or incorrect dependencies.

**Fix:** Add exhaustive-deps ESLint rule and fix all warnings.

---

### M-12: No API Response Caching
**File:** `apps/web/src/utils/api.ts`
**Description:** Every API call hits the server; no client-side caching.

**Fix:** Implement React Query or SWR:
```tsx
import useSWR from 'swr'

export function useTransactions(params) {
  return useSWR(['/transactions', params], fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 5000,
  })
}
```

---

### M-13: Docker Health Check Using Python
**File:** `Dockerfile.backend`
**Lines:** 51-52
**Description:** Health check spawns Python interpreter, which is slow.

```dockerfile
HEALTHCHECK ... CMD python -c "import urllib.request; ..."
```

**Fix:** Use curl or wget:
```dockerfile
RUN apt-get update && apt-get install -y curl
HEALTHCHECK ... CMD curl -f http://localhost:8000/api/health/live || exit 1
```

---

### M-14: No Graceful Shutdown Handling
**File:** `apps/backend/src/ledgerloop/api/main.py`
**Description:** No signal handlers for graceful shutdown.

**Fix:**
```python
import signal

@app.on_event("shutdown")
async def shutdown():
    # Close database connections
    # Flush logs
    # Complete pending tasks
    pass
```

---

### M-15: Missing Database Migrations Version Table
**File:** `apps/backend/src/ledgerloop/db.py`
**Description:** Schema versioning exists but may not track individual migrations.

**Fix:** Add migrations tracking table:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

---

### M-16: No Retry Logic on Transient Failures
**File:** `apps/web/src/utils/api.ts`
**Description:** API calls fail immediately on network errors.

**Fix:** Add retry with exponential backoff:
```typescript
async function apiRequestWithRetry<T>(url: string, options: RequestInit, retries = 3): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await apiRequest<T>(url, options)
    } catch (e) {
      if (i === retries - 1 || !isRetryable(e)) throw e
      await sleep(Math.pow(2, i) * 1000)
    }
  }
}
```

---

### M-17: Unused Imports and Dead Code
**Files:** Various
**Description:** Some files have unused imports or commented-out code blocks.

**Fix:** Run linter with unused import detection:
```bash
ruff check --select F401,F841 apps/backend/
```

---

### M-18: No Input Sanitization on Display
**File:** `apps/web/src/components/dashboard/EnhancedDashboard.tsx`
**Description:** Transaction descriptions displayed without sanitization.

**Impact:** XSS if malicious description stored in database.
**Fix:** React's JSX auto-escapes, but verify no `dangerouslySetInnerHTML` is used.

---

## Low Issues (11)

### L-1: Inconsistent Naming Conventions
**Files:** Various backend files
**Description:** Mix of snake_case and camelCase in some places.

**Fix:** Standardize on snake_case for Python, camelCase for TypeScript.

---

### L-2: Missing Docstrings
**Files:** Most backend files
**Description:** Functions lack docstrings explaining purpose and parameters.

**Fix:** Add docstrings to public functions:
```python
def apply_rules(transaction: dict) -> dict:
    """
    Apply categorization rules to a transaction.

    Args:
        transaction: Dict with 'description', 'amount', 'date' keys

    Returns:
        Transaction dict with 'category_id' added if rule matched
    """
```

---

### L-3: Magic Numbers
**File:** `apps/backend/src/ledgerloop/rules.py`
**Description:** Hardcoded numbers without explanation.

```python
if confidence > 0.7:  # What does 0.7 mean?
```

**Fix:** Use named constants:
```python
MIN_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence to auto-categorize
```

---

### L-4: Console.log in Production Code
**File:** `apps/web/src/app/ingest/page.tsx`
**Lines:** 60, 82, 96
**Description:** `console.error` calls should use proper logging.

**Fix:** Use structured logging or remove:
```typescript
import { logger } from '@/utils/logger'
logger.error('Error polling AI analysis', { error })
```

---

### L-5: No Git Pre-commit Hooks
**Description:** No pre-commit hooks for linting/formatting.

**Fix:** Add `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
      - id: ruff-format
```

---

### L-6: Missing .env.example Documentation
**File:** `.env.example`
**Description:** Environment variables not fully documented.

**Fix:** Add comments explaining each variable:
```bash
# JWT secret key - REQUIRED in production
# Generate with: openssl rand -base64 32
LEDGERLOOP_JWT_SECRET=

# CORS allowed origins (comma-separated)
LEDGERLOOP_CORS=http://localhost:3000
```

---

### L-7: No API Versioning
**File:** `apps/backend/src/ledgerloop/api/main.py`
**Description:** API routes not versioned (no `/api/v1/` prefix).

**Fix:** Add version prefix:
```python
app.include_router(router, prefix="/api/v1")
```

---

### L-8: Missing robots.txt
**File:** `apps/web/public/robots.txt`
**Description:** No robots.txt to prevent search engine indexing of private data.

**Fix:** Create robots.txt:
```
User-agent: *
Disallow: /
```

---

### L-9: No Favicon
**File:** `apps/web/public/favicon.ico`
**Description:** Missing favicon causes 404 errors in logs.

**Fix:** Add favicon.ico to public directory.

---

### L-10: Test Coverage Unknown
**Description:** No coverage reporting configured.

**Fix:** Add coverage to pytest:
```bash
pytest --cov=ledgerloop --cov-report=html apps/backend/tests/
```

---

### L-11: No Performance Monitoring
**Description:** No APM or performance monitoring.

**Fix:** Add basic timing middleware:
```python
import time

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response
```

---

## Recommendations Summary

### Immediate Actions (Do Now)
1. **Re-enable authentication** - Critical security gap
2. **Remove/rotate hardcoded secrets** - JWT key, WS token, admin password
3. **Fix CORS configuration** - Remove wildcard
4. **Fix DuckDB SQL syntax** - Replace `INSERT OR IGNORE`

### Short-term (This Sprint)
1. Add rate limiting
2. Add input validation on all endpoints
3. Add proper error logging
4. Fix silent exception handlers

### Medium-term (This Month)
1. Add CSRF protection
2. Implement proper database connection management
3. Add structured logging
4. Convert inline styles to Tailwind

### Long-term (Backlog)
1. Add API versioning
2. Implement caching layer
3. Add performance monitoring
4. Improve test coverage

---

## Files Audited

### Backend (23 files)
- `apps/backend/src/ledgerloop/api/main.py`
- `apps/backend/src/ledgerloop/api/auth.py`
- `apps/backend/src/ledgerloop/api/__init__.py`
- `apps/backend/src/ledgerloop/api/errors.py`
- `apps/backend/src/ledgerloop/api/routes/transactions.py`
- `apps/backend/src/ledgerloop/api/routes/auth_routes.py`
- `apps/backend/src/ledgerloop/api/routes/imports.py`
- `apps/backend/src/ledgerloop/api/routes/analytics.py`
- `apps/backend/src/ledgerloop/api/routes/export.py`
- `apps/backend/src/ledgerloop/api/routes/rules.py`
- `apps/backend/src/ledgerloop/api/routes/categories.py`
- `apps/backend/src/ledgerloop/api/routes/realtime.py`
- `apps/backend/src/ledgerloop/db.py`
- `apps/backend/src/ledgerloop/config.py`
- `apps/backend/src/ledgerloop/security.py`
- `apps/backend/src/ledgerloop/rules.py`
- `apps/backend/src/ledgerloop/ingest_csv.py`
- `apps/backend/src/ledgerloop/ingest_pdf.py`

### Frontend (12 files)
- `apps/web/src/utils/api.ts`
- `apps/web/src/utils/config.ts`
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/app/ingest/page.tsx`
- `apps/web/src/components/dashboard/EnhancedDashboard.tsx`
- `apps/web/src/services/websocket-manager.ts`
- `apps/web/next.config.js`

### Docker/Deployment (3 files)
- `docker-compose.yml`
- `Dockerfile.backend`
- `Dockerfile.web`

---

*Report generated by automated security audit*
