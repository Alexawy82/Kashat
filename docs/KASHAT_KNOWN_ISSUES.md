# KASHAT KNOWN ISSUES

**Last Updated:** 2025-12-28
**Status:** Pre-Release Testing Complete

---

## Outstanding Issues

### 1. Bills Page - Overdue Endpoint Returns Empty
- **Severity:** Low
- **Location:** `/bills` page, `/api/calendar/overdue` endpoint
- **Description:** The overdue bills endpoint always returns an empty array. The backend doesn't have due date tracking for recurring items to determine what's overdue.
- **Workaround:** Users can see upcoming bills in the calendar view
- **To Fix:** Add `due_date` field to recurring items and implement overdue calculation logic

### 2. Intelligence Feed Requires Request Body
- **Severity:** Low
- **Location:** `/api/intelligence/feed` endpoint
- **Description:** GET request returns 405, POST requires a request body. Currently not used by frontend.
- **Workaround:** Dashboard uses other analytics endpoints
- **To Fix:** Add proper request schema or change to GET endpoint

### 3. Transaction List Flicker on Category Change
- **Severity:** Low (Improved)
- **Location:** `/transactions` page
- **Description:** Previously the list would briefly disappear when categorizing transactions. Fixed with `keepPreviousData` and improved conditional rendering.
- **Status:** Mostly fixed - minor flicker may still occur in edge cases
- **To Fix:** Full optimistic updates with category name lookup

---

## Resolved During Testing

1. ✅ Deleted 6 redundant page directories (analytics, categories, rules, pulse, calendar, recurring)
2. ✅ All 6 redirects configured and working
3. ✅ Build passes with no TypeScript errors
4. ✅ All 12 pages load successfully
5. ✅ 100% category coverage (2118/2118 transactions)

---

## Not Issues (Expected Behavior)

- **Empty budgets list:** No budgets created yet - this is expected
- **Empty assets/liabilities:** User hasn't added any manual assets yet
- **Metal prices null:** API needs to be called to fetch live prices

---

*Document generated during pre-release testing on 2025-12-28*
