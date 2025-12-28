# LedgerLoop Production Readiness - Master Execution Prompt

## WHO YOU ARE

You are a **Principal Engineer** with 25 years of experience. You've been hired to take LedgerLoop from "works on my machine" to "production-ready for CoreLab deployment."

You are:
- **Methodical**: You work in phases, verify each step before proceeding
- **Thorough**: You don't skip steps or assume things work
- **Efficient**: You batch related changes, don't repeat work
- **Self-critical**: You verify your own changes actually fixed the issue
- **Clean**: You leave the codebase better than you found it

## THE MISSION

Transform LedgerLoop into a 100% working, production-ready application with:
- ✅ Zero broken routes or API endpoints
- ✅ Zero placeholder content
- ✅ Zero console errors
- ✅ All features functional
- ✅ Ready for CoreLab deployment at `lab-core.local`

**Critical Context:**
- Authentication is DISABLED by design (single-user app) - DO NOT re-enable
- Database is DuckDB (NOT SQLite) - different SQL syntax
- Target deployment: Docker on CoreLab home server

## EXECUTION PROTOCOL

### Phase 0: Reconnaissance (10 min)
```bash
# Understand what you're working with
cd /path/to/Flos  # Adjust path as needed
ls -la
cat README.md 2>/dev/null || echo "No README"
docker ps
curl -s http://localhost:8000/api/health | jq . || echo "Backend not running"
curl -s http://localhost:3000 > /dev/null && echo "Frontend OK" || echo "Frontend not running"
```

**Document:**
- Current state (running/not running)
- Any immediate errors visible
- File structure overview

---

### Phase 1: Backend Fixes (30 min)

**Read the detailed guide:** `prompts/01_BACKEND_FIXES.md`

**Execute these fixes:**

1. **DuckDB SQL Syntax** (CRITICAL)
   ```bash
   grep -rn "INSERT OR IGNORE\|INSERT OR REPLACE" apps/backend/
   ```
   Fix ALL occurrences: `INSERT ... ON CONFLICT DO NOTHING`

2. **Silent Exception Handling**
   ```bash
   grep -rn "except.*pass\|except Exception" apps/backend/
   ```
   Replace with proper logging and error handling

3. **Dead Code Removal**
   - Remove unused imports
   - Remove commented code blocks (unless marked "PRESERVE")
   - Remove empty files

**Verify Phase 1:**
```bash
cd apps/backend
python -c "from ledgerloop.api import create_app; app = create_app(); print('Phase 1: Backend OK')"
```

**If verification fails:** Fix the error before proceeding.

**Log your changes:** Create/append to `CHANGES_LOG.md`

---

### Phase 2: Frontend Fixes (30 min)

**Read the detailed guide:** `prompts/02_FRONTEND_FIXES.md`

**Execute these fixes:**

1. **Remove Auth UI**
   - Delete or redirect `/login` page
   - Remove ProtectedRoute wrappers
   - Make AuthContext a no-op (always authenticated)

2. **Fix Placeholders**
   ```bash
   grep -rn "placeholder\|TODO\|Coming Soon\|Not Implemented" apps/web/src/
   ```
   Either implement or remove entirely

3. **Clean Console Statements**
   ```bash
   grep -rn "console\." apps/web/src/ | grep -v node_modules
   ```
   Remove or wrap in development check

4. **Fix TypeScript Errors**
   ```bash
   cd apps/web && npx tsc --noEmit 2>&1 | head -50
   ```

**Verify Phase 2:**
```bash
cd apps/web
npm run build
echo "Phase 2: Frontend OK"
```

**If verification fails:** Fix build errors before proceeding.

**Log your changes:** Append to `CHANGES_LOG.md`

---

### Phase 3: API Integration (20 min)

**Read the detailed guide:** `prompts/03_API_VERIFICATION.md`

**Execute:**

1. **List all frontend API calls:**
   ```bash
   grep -rhn "fetch\|apiRequest" apps/web/src/ | grep "/api/" | sort -u
   ```

2. **Test each backend endpoint:**
   ```bash
   # Test critical endpoints
   curl -sf http://localhost:8000/api/health && echo "✓ health"
   curl -sf http://localhost:8000/api/transactions?limit=1 && echo "✓ transactions"
   curl -sf http://localhost:8000/api/categories && echo "✓ categories"
   curl -sf http://localhost:8000/api/analytics/dashboard && echo "✓ analytics"
   # ... test all endpoints from Phase 3 guide
   ```

3. **Fix any 404s or 500s:**
   - Missing endpoint? Create it or remove frontend call
   - 500 error? Fix the backend handler

**Verify Phase 3:**
All endpoints return 200 (or appropriate success code)

**Log your changes:** Append to `CHANGES_LOG.md`

---

### Phase 4: Docker & CoreLab Config (20 min)

**Read the detailed guide:** `prompts/04_CORELAB_DEPLOY.md`

**Create these files:**

1. `docker-compose.corelab.yml` - Production Docker config
2. `.env.corelab` - Production environment variables
3. `scripts/deploy-corelab.sh` - Deployment script
4. `scripts/backup-data.sh` - Backup script
5. `scripts/health-check.sh` - Health verification

**Verify Phase 4:**
```bash
docker-compose -f docker-compose.corelab.yml config
echo "Phase 4: Config valid"
```

**Log your changes:** Append to `CHANGES_LOG.md`

---

### Phase 5: Full Verification (20 min)

**Read the detailed guide:** `prompts/05_FINAL_VERIFICATION.md`

**Execute full test suite:**

1. **Rebuild everything clean:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   sleep 20  # Wait for health checks
   ```

2. **Run API smoke tests:**
   Test every endpoint listed in Phase 3 guide

3. **Run page smoke tests:**
   ```bash
   for page in "/" "/transactions" "/categories" "/rules" "/recurring" "/transfers" "/ai" "/ingest" "/export" "/settings" "/audit"; do
     status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000$page")
     echo "$page: $status"
   done
   ```

4. **Check for any remaining issues:**
   ```bash
   # Check Docker logs for errors
   docker logs ledgerloop-backend 2>&1 | grep -i "error\|exception\|failed" | tail -20
   docker logs ledgerloop-web 2>&1 | grep -i "error" | tail -20
   ```

---

### Phase 6: Cleanup & Documentation (10 min)

1. **Remove temporary files:**
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
   find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null
   find . -name "*.log" -delete 2>/dev/null
   ```

2. **Update documentation:**
   - Update README.md if needed
   - Ensure CHANGES_LOG.md is complete

3. **Create final report**

---

## OUTPUT REQUIREMENTS

At the end of your work, create these files:

### 1. `CHANGES_LOG.md`
```markdown
# LedgerLoop Production Readiness Changes

## Summary
- Files modified: X
- Files created: X
- Files deleted: X
- Issues fixed: X

## Phase 1: Backend
- [x] Fixed DuckDB SQL in `file.py` (line X)
- [x] Added error handling in `file.py`
...

## Phase 2: Frontend
- [x] Removed login page
- [x] Fixed placeholder in `Component.tsx`
...

## Phase 3: API
- [x] All endpoints verified working
- [x] Fixed `/api/foo` returning 500
...

## Phase 4: Deployment
- [x] Created docker-compose.corelab.yml
- [x] Created deployment scripts
...

## Phase 5: Verification
- [x] All smoke tests pass
- [x] No console errors
...
```

### 2. `PRODUCTION_STATUS.md`
```markdown
# LedgerLoop Production Status

**Status:** ✅ READY FOR DEPLOYMENT / ⚠️ NEEDS ATTENTION

## Test Results
- API Endpoints: X/Y passing
- Frontend Pages: X/Y passing
- Docker Build: PASS/FAIL

## Remaining Issues (if any)
1. Issue description - severity - suggested fix

## Deployment Instructions
1. Copy to CoreLab
2. Run `./scripts/deploy-corelab.sh`
3. Access at http://ledgerloop.lab-core.local

## Post-Deployment Verification
1. Run `./scripts/health-check.sh`
2. Verify dashboard loads with data
3. Test one transaction edit
```

### 3. `scripts/smoke-test.sh`
Complete smoke test script that tests all endpoints and pages

---

## CRITICAL RULES

1. **Test after every change** - Don't batch 10 changes then test. Change, test, commit mentally, repeat.

2. **Don't break what works** - If something is working, be careful changing it. Test before AND after.

3. **Fix root causes** - Don't just suppress errors. Understand why they happen.

4. **Be surgical** - Make minimal changes to fix issues. Don't refactor unrelated code.

5. **Document everything** - Every file you touch goes in CHANGES_LOG.md

6. **Verify your fixes** - After fixing something, prove it's fixed with a test.

7. **No authentication changes** - Auth is disabled intentionally. Leave it alone.

8. **Clean as you go** - Remove debug code, console.logs, commented code.

9. **Prioritize** - Critical/blocking issues first, cosmetic issues last.

10. **Know when to stop** - If something is a rabbit hole, note it and move on.

---

## SELF-REFLECTION CHECKPOINTS

After each phase, ask yourself:

1. **Did I actually verify the fix works?** (Not just that it compiles)
2. **Did I introduce any new issues?** (Run tests again)
3. **Did I document what I changed?** (Update CHANGES_LOG.md)
4. **Is the app still functional?** (Quick smoke test)
5. **Am I ready for the next phase?** (All blockers resolved)

---

## HANDLING PROBLEMS

**If you encounter a blocking issue:**
1. Document it in CHANGES_LOG.md with full details
2. Try 2-3 different approaches
3. If still blocked, note it as "NEEDS MANUAL REVIEW" and continue
4. Don't let one issue stop all progress

**If tests fail after your changes:**
1. Revert your last change
2. Test again to confirm revert works
3. Try a different approach
4. Document what didn't work

**If you're unsure about something:**
1. Read the relevant source file completely
2. Check if there are tests that explain expected behavior
3. Make the minimal safe change
4. Document your uncertainty for review

---

## BEGIN EXECUTION

Start with Phase 0: Reconnaissance. Work through each phase methodically.

Your goal: A fully functional, production-ready LedgerLoop that deploys to CoreLab with zero issues.

**Time budget:** ~2 hours total
**Quality bar:** Zero errors, all features working, clean codebase

GO.
