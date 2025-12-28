# Phase 1: Backend Fixes

## Your Role
You are a senior Python/FastAPI developer. Fix all backend issues to make this production-ready.

## Context
- App: LedgerLoop (personal finance)
- Backend: `apps/backend/src/ledgerloop/`
- Database: DuckDB (NOT SQLite - different SQL syntax!)
- Auth: DISABLED intentionally (single-user app) - DO NOT re-enable

## Critical Fixes Required

### 1. DuckDB SQL Syntax (HIGHEST PRIORITY)

DuckDB does NOT support `INSERT OR IGNORE`. Find and fix ALL occurrences.

**Search for:**
```bash
grep -r "INSERT OR IGNORE" apps/backend/
grep -r "INSERT OR REPLACE" apps/backend/
```

**Replace with DuckDB syntax:**
```sql
-- WRONG (SQLite):
INSERT OR IGNORE INTO table (col) VALUES (val)

-- CORRECT (DuckDB):
INSERT INTO table (col) VALUES (val) ON CONFLICT DO NOTHING

-- For upsert:
INSERT INTO table (col) VALUES (val) 
ON CONFLICT (key_col) DO UPDATE SET col = excluded.col
```

Files likely affected:
- `db/database.py`
- `db/repositories/*.py`
- Any file with raw SQL

### 2. Silent Exception Handling

Find and fix all `except: pass` or `except Exception: pass` patterns.

**Search for:**
```bash
grep -rn "except.*pass" apps/backend/
grep -rn "except Exception" apps/backend/
```

**Replace with proper handling:**
```python
# WRONG:
try:
    do_something()
except:
    pass

# CORRECT:
import logging
logger = logging.getLogger(__name__)

try:
    do_something()
except SpecificException as e:
    logger.warning(f"Expected error handled: {e}")
except Exception as e:
    logger.error(f"Unexpected error in do_something: {e}", exc_info=True)
    raise  # or return appropriate error response
```

### 3. Remove Dead Code

Find and remove:
- Unused imports
- Commented-out code blocks (unless marked as intentionally preserved)
- Unused functions/classes
- Empty files

**Check:**
```bash
# Find unused imports (manual review)
grep -r "^import\|^from" apps/backend/src/ledgerloop/

# Find TODO/FIXME that need resolution
grep -rn "TODO\|FIXME\|XXX\|HACK" apps/backend/
```

### 4. Fix Hardcoded Values

Replace hardcoded values with environment variables or config:

```python
# WRONG:
SECRET_KEY = "changeme"
DEFAULT_LIMIT = 100

# CORRECT:
import os
SECRET_KEY = os.getenv("LEDGERLOOP_SECRET_KEY", "dev-only-default")
DEFAULT_LIMIT = int(os.getenv("LEDGERLOOP_DEFAULT_LIMIT", "100"))
```

### 5. API Response Consistency

Ensure ALL endpoints return consistent response format:

```python
# Success responses:
{"data": [...], "meta": {"total": N, "page": 1}}
# or
{"data": {...}}

# Error responses:
{"error": {"message": "...", "code": "ERROR_CODE"}}
```

### 6. Verify All Routes Work

Test each route file exists and endpoints are valid:
- `api/routes/transactions.py`
- `api/routes/categories.py`
- `api/routes/rules.py`
- `api/routes/recurring.py`
- `api/routes/transfers.py`
- `api/routes/analytics.py`
- `api/routes/ai_routes.py`
- `api/routes/import_routes.py`
- `api/routes/export_routes.py`
- `api/routes/settings.py`
- `api/routes/audit.py`
- `api/routes/admin.py`

## Execution Steps

1. **Read first**: 
   ```bash
   ls -la apps/backend/src/ledgerloop/
   ls -la apps/backend/src/ledgerloop/api/routes/
   ls -la apps/backend/src/ledgerloop/db/
   ```

2. **Fix SQL syntax** in all files

3. **Fix exception handling** throughout

4. **Remove dead code** carefully

5. **Test after each fix**:
   ```bash
   cd apps/backend
   python -c "from ledgerloop.api import create_app; app = create_app(); print('OK')"
   ```

## Output Required

Create `BACKEND_FIXES_LOG.md` documenting:
- Files modified
- What was changed
- Any issues found that need frontend changes

## Rules
- DO NOT touch authentication code (it's disabled intentionally)
- DO NOT change API endpoint URLs (frontend depends on them)
- DO test that imports still work after changes
- DO preserve the auth code commented out for future use
