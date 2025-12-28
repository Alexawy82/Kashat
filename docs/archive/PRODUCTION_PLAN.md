# LedgerLoop Production Readiness Plan

## Overview
Get LedgerLoop 100% clean and production-ready for CoreLab deployment.

**Key Decisions:**
- ✅ NO authentication needed (single-user, home network)
- ✅ Target: CoreLab home server (lab-core.local)
- ✅ Docker deployment
- ✅ All features must work - no placeholders, no broken routes

## Execution Order

Run these prompts in order with Claude CLI:

```bash
cd C:\Users\Marwan\Desktop\AI\Flos

# Phase 1: Backend fixes (SQL, error handling, dead code)
claude -p prompts/01_BACKEND_FIXES.md

# Phase 2: Frontend fixes (broken routes, placeholders, cleanup)  
claude -p prompts/02_FRONTEND_FIXES.md

# Phase 3: API integration verification
claude -p prompts/03_API_VERIFICATION.md

# Phase 4: Docker & CoreLab deployment config
claude -p prompts/04_CORELAB_DEPLOY.md

# Phase 5: Final verification & testing
claude -p prompts/05_FINAL_VERIFICATION.md
```

## What Each Phase Does

### Phase 1: Backend Fixes
- Fix DuckDB SQL syntax issues (INSERT OR IGNORE → INSERT ... ON CONFLICT)
- Replace silent `except: pass` with proper error handling
- Remove dead/unused code
- Fix any broken service logic
- Ensure all API endpoints return proper responses

### Phase 2: Frontend Fixes
- Remove/fix placeholder components
- Fix broken navigation links
- Remove orphaned pages
- Clean up console.logs
- Ensure all pages load without errors
- Fix any TypeScript errors

### Phase 3: API Integration
- Verify every frontend API call has working backend endpoint
- Fix any mismatched types between frontend/backend
- Test all CRUD operations work end-to-end
- Document any missing endpoints

### Phase 4: CoreLab Deployment
- Configure docker-compose for CoreLab
- Set up proper environment variables
- Configure networking for lab-core.local
- Create deployment script
- Set up data persistence

### Phase 5: Final Verification
- Run full test suite
- Test every page manually
- Verify all features work
- Create smoke test script
- Generate deployment checklist

## Files Created
After running all phases, you'll have:
- Clean, working codebase
- `CORELAB_DEPLOY.md` - Deployment guide
- `docker-compose.corelab.yml` - Production config
- `scripts/smoke_test.sh` - Verification script
- `CHANGELOG.md` - What was fixed
