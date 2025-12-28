# KASHAT BACKEND ROUTE FIX
## For Claude Code CLI

---

## PROBLEM

The backend has route files for:
- `/api/networth` - Net worth calculation
- `/api/budgets` - Budget system
- `/api/calendar` - Bill calendar
- `/api/insights` - Smart insights

But they return 404 because the running server hasn't loaded them.

**Location**: `C:\Users\Marwan\Desktop\AI\Flos\apps\backend`

---

## PHASE 1: DIAGNOSE

### 1.1 Check if Backend is Running

```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Or try to hit health endpoint
curl http://localhost:8000/api/health
```

### 1.2 Check Current Routes

```bash
# Get list of registered routes
curl http://localhost:8000/openapi.json | python -c "import sys,json; paths=json.load(sys.stdin)['paths']; print('\n'.join(sorted(paths.keys())))" | findstr "networth budget calendar insights"
```

If no results, the routes aren't registered.

---

## PHASE 2: CLEAR PYTHON CACHE

Python caches compiled modules. Clear them to force reload.

```powershell
# Navigate to backend
cd C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src

# Remove all __pycache__ directories
Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force

# Or specifically:
Remove-Item -Recurse -Force kashat\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force kashat\api\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force kashat\api\routes\__pycache__ -ErrorAction SilentlyContinue
```

---

## PHASE 3: FIND AND KILL EXISTING BACKEND

```powershell
# Find process on port 8000
$process = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($process) {
    $pid = $process.OwningProcess
    Write-Host "Found backend process: PID $pid"
    Stop-Process -Id $pid -Force
    Write-Host "Killed process $pid"
} else {
    Write-Host "No process found on port 8000"
}
```

Or manually:
```powershell
# Find PID
netstat -ano | findstr :8000

# Kill it (replace XXXX with actual PID)
taskkill /PID XXXX /F
```

---

## PHASE 4: RESTART BACKEND

```powershell
# Navigate to backend directory
cd C:\Users\Marwan\Desktop\AI\Flos\apps\backend

# Start the backend (this will block the terminal)
python -m kashat.api.main
```

**Expected Output:**
```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

If there are import errors, they will show here.

---

## PHASE 5: VERIFY ROUTES ARE LOADED

In a NEW terminal:

```powershell
# Test networth endpoint
curl http://localhost:8000/api/networth
# Expected: JSON with assets, liabilities, net_worth

# Test budgets endpoint
curl http://localhost:8000/api/budgets
# Expected: JSON array (possibly empty [])

# Test calendar endpoint
curl http://localhost:8000/api/calendar/upcoming
# Expected: JSON with upcoming bills

# Test insights endpoint
curl http://localhost:8000/api/insights/cards
# Expected: JSON with insight cards

# Verify in OpenAPI
curl -s http://localhost:8000/openapi.json | python -c "import sys,json; paths=json.load(sys.stdin)['paths']; matches=[p for p in paths if 'networth' in p or 'budget' in p or 'calendar' in p or 'insights' in p]; print(f'Found {len(matches)} routes:'); [print(f'  {p}') for p in sorted(matches)]"
```

---

## PHASE 6: VERIFY FRONTEND WORKS

```bash
# Refresh the browser at http://localhost:3000
# Dashboard should now show:
# - Net Worth card (with actual values)
# - Budget summary (may be empty if no budgets created)
# - Upcoming bills (from recurring detection)
# - Insight cards

# Check browser console - should NOT have 404 errors for these endpoints
```

---

## TROUBLESHOOTING

### If Import Error on Startup

Check the backend terminal for errors like:
```
ImportError: cannot import name 'X' from 'Y'
ModuleNotFoundError: No module named 'X'
```

Fix by installing missing package:
```bash
cd C:\Users\Marwan\Desktop\AI\Flos\apps\backend
pip install <missing-package>
```

### If Routes Still 404 After Restart

Check that routes are actually in the code:

```powershell
# Verify networth router exists and has correct prefix
Select-String -Path "C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src\kashat\api\routes\networth.py" -Pattern "prefix"

# Verify it's imported in __init__.py
Select-String -Path "C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src\kashat\api\__init__.py" -Pattern "networth"

# Verify it's registered
Select-String -Path "C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src\kashat\api\__init__.py" -Pattern "include_router.*networth"
```

### If Backend Won't Start

Check for syntax errors:
```powershell
cd C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src
python -m py_compile kashat\api\routes\networth.py
python -m py_compile kashat\api\routes\budgets.py
python -m py_compile kashat\api\routes\calendar.py
python -m py_compile kashat\api\routes\insights.py
```

---

## SUCCESS CRITERIA

After fix:

| Endpoint | Expected Response |
|----------|-------------------|
| `GET /api/networth` | `{"assets": X, "liabilities": Y, "net_worth": Z, ...}` |
| `GET /api/budgets` | `[]` or list of budgets |
| `GET /api/calendar/upcoming` | `{"bills": [...], ...}` |
| `GET /api/insights/cards` | `{"cards": [...], ...}` |

Dashboard should show:
- ✅ Net Worth card with values
- ✅ Budget summary (or empty state)
- ✅ Upcoming bills widget
- ✅ Smart insights cards
- ✅ No 404 errors in browser console

---

## QUICK ONE-LINER

If you just want to restart everything:

```powershell
# Kill backend, clear cache, restart
$p = Get-NetTCPConnection -LocalPort 8000 -EA 0 | Select -First 1; if($p){Stop-Process -Id $p.OwningProcess -Force}; cd C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src; Get-ChildItem -Filter __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force; cd ..; python -m kashat.api.main
```

---

*Routes are built. Just need the server to load them.*
