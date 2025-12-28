# KASHAT UI ISSUES & RECOMMENDATIONS

## Summary
- **Critical Issues:** 4
- **Redundancies:** 4 pages, 3 features
- **UX Problems:** 8
- **Missing Features:** 3
- **Type Safety Issues:** 4 pages
- **Dead Code Candidates:** 6 components

---

## Critical Issues

### 1. Budget Progress Endpoint Missing
**Location:** `/budget` page
**Issue:** `GET /api/budgets/{id}/progress` endpoint doesn't exist
**Impact:** Budget progress bars don't show actual spending
**Fix Required:** Implement endpoint or remove progress display

### 2. Calendar Overdue Returns Empty
**Location:** `/calendar` page
**Issue:** `GET /api/calendar/overdue` always returns `[]`
**Impact:** Overdue bills section never shows anything
**Reason:** Backend schema lacks `next_date` tracking for recurring series
**Fix Required:** Implement date tracking or remove overdue section

### 3. Service Filter Not Implemented
**Location:** `/transfers` page
**Issue:** Service filter dropdown in UI doesn't work
**Impact:** Users can select service (Zelle, Venmo, etc.) but nothing filters
**Fix Required:** Wire up filter to API or remove dropdown

### 4. Link Recurring Button is Stub
**Location:** `/transfers` page
**Issue:** "Link Recurring" button only does `console.log()`
**Impact:** Feature advertised but non-functional
**Fix Required:** Implement or remove button

---

## Broken Features

| Page | Component | Issue | Severity |
|------|-----------|-------|----------|
| Budget | Progress bars | No data (missing endpoint) | High |
| Calendar | Overdue bills | Always empty | Medium |
| Transfers | Service filter | Not wired up | Low |
| Transfers | Link Recurring | console.log only | Low |
| Import | Upload progress | No progress indicator | Low |
| Import | File size limit | 50MB not enforced client-side | Low |

---

## Redundancy Map

### Page-Level Redundancies

| Duplicate Page | Original Page | Overlap | Recommendation |
|----------------|---------------|---------|----------------|
| `/analytics` | Dashboard (Spending/Trends/Forecast tabs) | 90% | Remove `/analytics`, enhance Dashboard |
| `/categories` | `/settings/categories` | 100% | Remove `/categories` |
| `/rules` | `/settings/automation` | 100% | Remove `/rules` |
| `/pulse` | `/settings/system` | 100% | Remove `/pulse` |

### Feature Redundancies

| Feature | Location 1 | Location 2 | Keep |
|---------|------------|------------|------|
| Spending charts | Dashboard > Spending | Analytics | Dashboard |
| AI Trends | Dashboard > Trends | Analytics | Dashboard |
| Forecasts | Dashboard > Forecast | Analytics | Dashboard |
| Category management | /settings/categories | /categories | Settings |
| Rule management | /settings/automation | /rules | Settings |
| System health | /settings/system | /pulse | Settings |

---

## UX Confusion Points

### 1. Net Worth Hidden in Tab
**Location:** Dashboard
**Problem:** Net Worth card only visible in Overview tab, not immediately visible
**Suggestion:** Make net worth always visible at top of dashboard

### 2. Too Many Dashboard Tabs
**Location:** Dashboard
**Problem:** 4 tabs (Overview, Spending, Trends, Forecast) - user must click around
**Suggestion:** Consolidate to 2 tabs max or single scrollable page

### 3. Settings Too Deep
**Location:** Settings pages
**Problem:** Key features (categories, rules) buried under Settings
**Current:** Settings > Categories, Settings > Automation
**Suggestion:** Promote Categories and Rules to sidebar if frequently used

### 4. Import Has No Progress
**Location:** Import page
**Problem:** File uploads show no progress bar, unclear if working
**Suggestion:** Add upload progress indicator

### 5. Calendar is Read-Only
**Location:** Calendar page
**Problem:** Can only view dates, can't add/edit bills
**Suggestion:** Add ability to create bills from calendar

### 6. Recurring Has Too Many Tabs
**Location:** Recurring page
**Problem:** 6 tabs (All, Subscriptions, Housing, Loans, Credit Cards, Insurance)
**Suggestion:** Use filter dropdown instead of tabs

### 7. Browser Confirm for Deletes
**Location:** Import, Recurring, Transfers
**Problem:** Uses browser `confirm()` dialog, not styled modal
**Suggestion:** Use proper confirmation dialog component

### 8. Inconsistent Loading States
**Location:** All dashboard cards
**Problem:** Some use CardSkeleton, others use Loader2 spinner
**Suggestion:** Standardize on CardSkeleton for all cards

---

## Missing Features

### 1. Budget Edit/Update
**Location:** Budget page
**Issue:** Can create budgets but can't edit or update them
**Impact:** Users must delete and recreate budgets

### 2. Transaction Editing
**Location:** Transactions page
**Issue:** No inline editing of transactions
**Impact:** Can't fix merchant names, amounts, dates

### 3. Bulk Export
**Location:** Settings > Data
**Issue:** Export button exists but feature limited
**Impact:** Can't export specific date ranges or accounts

---

## Type Safety Issues

| Page | File | Issue |
|------|------|-------|
| Dashboard | page.tsx:342 | `merchant: any` |
| Transactions | page.tsx | Multiple `any` casts |
| Analytics | page.tsx | Heavy `any` usage |
| Settings | All sub-pages | Unsafe type assertions |

---

## Missing Error Handling

### Components Without Error Boundaries
- All 11 dashboard cards (one error breaks entire dashboard)
- All 3 chart components
- Transaction table
- Recurring patterns table

### Missing Loading States
- Some settings forms
- Category tree view
- Rule builder

---

## Accessibility Issues

| Issue | Location | Impact |
|-------|----------|--------|
| Date inputs lack labels | Import, Calendar filters | Screen readers can't identify |
| Icons missing aria-labels | Throughout sidebar, actions | Buttons not accessible |
| Category tree uses divs | Settings > Categories | Not navigable by keyboard |
| Focus management missing | All modals | Tab order issues |

---

## Dead Code Candidates

### Potentially Unused Components
| Component | File | Reason |
|-----------|------|--------|
| BottomNav | layout/BottomNav.tsx | Mobile nav, check if rendered |
| MobileNav | layout/MobileNav.tsx | Mobile nav, check if rendered |
| EmptyState | ui/EmptyState.tsx | Verify actual usage |
| CategoryPieChart | charts/CategoryPieChart.tsx | Only on Analytics (being removed) |
| MonthlyBarChart | charts/MonthlyBarChart.tsx | Only on Analytics (being removed) |

### Duplicate Route Files
| File | Duplicate Of |
|------|--------------|
| `/categories/page.tsx` | `/settings/categories/page.tsx` |
| `/rules/page.tsx` | `/settings/automation/page.tsx` |
| `/pulse/page.tsx` | `/settings/system/page.tsx` |

---

## API Endpoint Issues

### Missing Endpoints
| Expected Endpoint | Used By | Status |
|-------------------|---------|--------|
| GET /api/budgets/{id}/progress | Budget page | Not implemented |

### Endpoints Returning Empty
| Endpoint | Reason |
|----------|--------|
| GET /api/calendar/overdue | No next_date tracking in schema |
| GET /api/insights/price-increases | No price_hike tracking in schema |

### Underutilized Endpoints
| Endpoint | Issue |
|----------|-------|
| POST /api/p2p/enrich | Called but result not shown |
| POST /api/recurring/detect | Works but no progress indicator |

---

## Performance Concerns

### 1. Dashboard Makes Too Many API Calls
**Issue:** Dashboard uses 11 hooks, each making separate API calls
**Impact:** Slow initial load, waterfall requests
**Fix:** Combine related endpoints or add data loading strategy

### 2. No Pagination in Some Lists
**Issue:** Recurring, Transfers load all items at once
**Impact:** Slow with many records
**Fix:** Add pagination like Transactions page has

### 3. Heavy Re-renders
**Issue:** Some components lack proper memoization
**Impact:** Unnecessary re-renders on state changes
**Fix:** Add React.memo and useMemo where appropriate

---

## Priority Fix Order

### P0 - Critical (Fix Immediately)
1. Budget progress endpoint
2. Overdue bills (remove section or implement)

### P1 - High (Fix This Sprint)
1. Remove redundant pages (/analytics, /categories, /rules, /pulse)
2. Wire up Transfers service filter
3. Remove or implement Link Recurring button

### P2 - Medium (Fix Soon)
1. Add error boundaries to dashboard cards
2. Standardize loading states
3. Fix type safety issues

### P3 - Low (Backlog)
1. Accessibility improvements
2. Performance optimizations
3. Dead code cleanup

---

*Generated: 2025-12-27*
