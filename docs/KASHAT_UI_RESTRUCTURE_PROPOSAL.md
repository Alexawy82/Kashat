# KASHAT UI RESTRUCTURE PROPOSAL

## Executive Summary

The Kashat UI has grown organically and now contains significant redundancy, confusing navigation, and broken features. This proposal outlines a restructured UI that is cleaner, more intuitive, and eliminates duplicate functionality.

**Key Changes:**
- Remove 4 redundant pages
- Consolidate Dashboard to 2 tabs
- Promote frequently-used features to sidebar
- Fix all broken endpoints
- Standardize component patterns

---

## Current Problems

### 1. Page Redundancy (4 pages)
- `/analytics` duplicates Dashboard Spending/Trends/Forecast tabs (90% overlap)
- `/categories` duplicates `/settings/categories` (100% identical)
- `/rules` duplicates `/settings/automation` (100% identical)
- `/pulse` duplicates `/settings/system` (100% identical)

### 2. Dashboard Complexity
- 4 tabs with overlapping content
- 11 widgets competing for attention
- Net worth hidden in tab

### 3. Broken Features
- Budget progress not working
- Calendar overdue always empty
- Transfers filter non-functional

### 4. Navigation Confusion
- Too many entry points to same features
- Settings contains important daily-use features
- Unclear hierarchy

---

## Proposed New Structure

### Sidebar Navigation (Simplified)

```
Current (9 items):          Proposed (8 items):
├── Dashboard              ├── Dashboard (enhanced)
├── Transactions           ├── Transactions
├── Import                 ├── Import
├── Calendar               ├── Bills (renamed from Calendar)
├── Recurring              ├── Subscriptions (renamed from Recurring)
├── Budget                 ├── Budget (fixed)
├── Transfers              ├── Transfers
├── Analytics  ← REMOVE    └── Settings
└── Settings                   ├── Categories
                               ├── Automation
                               ├── AI Settings
                               └── System
```

### Changes Explained

| Current | Proposed | Reason |
|---------|----------|--------|
| Dashboard + Analytics | Dashboard (unified) | Eliminate 90% duplication |
| Calendar | Bills | Clearer purpose |
| Recurring | Subscriptions | More descriptive |
| /categories | Settings > Categories | Consolidate |
| /rules | Settings > Automation | Consolidate |
| /pulse | Settings > System | Consolidate |

---

## Dashboard Redesign

### Current Dashboard (4 tabs, 11+ widgets)
```
┌─────────────────────────────────────────────────────────────┐
│ [Overview] [Spending] [Trends] [Forecast]                   │
├─────────────────────────────────────────────────────────────┤
│ Overview Tab:                                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │ NetWorth │ │ Cashflow │ │ Budget   │ │ Health   │        │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│ │ Runway   │ │ Bills    │ │ Behavior │                     │
│ └──────────┘ └──────────┘ └──────────┘                     │
│ ┌──────────────────────────────────────┐                   │
│ │ AI Insights + Intelligence Feed      │                   │
│ └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Proposed Dashboard (2 tabs, focused)
```
┌─────────────────────────────────────────────────────────────┐
│ [Overview] [Insights]                                       │
├─────────────────────────────────────────────────────────────┤
│ ALWAYS VISIBLE:                                             │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Net Worth: $XX,XXX  │  This Month: +$X,XXX  │  Health: A ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
│ Overview Tab:                                               │
│ ┌────────────────────────┐ ┌────────────────────────────┐  │
│ │ Spending Chart         │ │ Top Categories             │  │
│ │ (Income vs Expenses)   │ │ (Pie chart)                │  │
│ └────────────────────────┘ └────────────────────────────┘  │
│ ┌────────────────────────┐ ┌────────────────────────────┐  │
│ │ Upcoming Bills (7 days)│ │ Recent Transactions        │  │
│ └────────────────────────┘ └────────────────────────────┘  │
│                                                             │
│ Insights Tab:                                               │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ AI Spending Patterns + Trends + Forecasts              │ │
│ │ (Scrollable feed of AI insights)                       │ │
│ └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Dashboard Changes
1. **Always-visible header** with Net Worth, Monthly Summary, Health Score
2. **2 tabs instead of 4** (Overview for data, Insights for AI)
3. **Remove widgets**: Runway, SpendingBehavior, RecurringSummary (moved to respective pages)
4. **Absorb Analytics**: All analytics content now in Dashboard

---

## Page-by-Page Changes

### Pages to DELETE

| Page | Route | Action |
|------|-------|--------|
| Analytics | `/analytics` | DELETE - content moved to Dashboard |
| Categories | `/categories` | DELETE - use `/settings/categories` |
| Rules | `/rules` | DELETE - use `/settings/automation` |
| Pulse | `/pulse` | DELETE - use `/settings/system` |

### Pages to RENAME

| Current | New Name | New Route | Reason |
|---------|----------|-----------|--------|
| Calendar | Bills | `/bills` | More descriptive |
| Recurring | Subscriptions | `/subscriptions` | Industry standard term |

### Pages to FIX

| Page | Issue | Fix |
|------|-------|-----|
| Budget | Progress not working | Implement `/api/budgets/{id}/progress` |
| Bills (Calendar) | Overdue empty | Either fix or remove section |
| Transfers | Filter broken | Wire up service filter |

---

## Files to Delete

### Frontend Pages (4 files)
```
apps/web/src/app/analytics/page.tsx      ← DELETE
apps/web/src/app/categories/page.tsx     ← DELETE
apps/web/src/app/rules/page.tsx          ← DELETE
apps/web/src/app/pulse/page.tsx          ← DELETE
```

### Potentially Unused Components (verify first)
```
apps/web/src/components/layout/BottomNav.tsx     ← CHECK USAGE
apps/web/src/components/layout/MobileNav.tsx     ← CHECK USAGE
apps/web/src/components/ui/EmptyState.tsx        ← CHECK USAGE
```

---

## Files to Modify

### Sidebar Navigation
**File:** `apps/web/src/components/layout/Sidebar.tsx`

```tsx
// CURRENT NAV ITEMS
const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/" },
  { icon: ArrowLeftRight, label: "Transactions", href: "/transactions" },
  { icon: Upload, label: "Import", href: "/import" },
  { icon: Calendar, label: "Calendar", href: "/calendar" },
  { icon: Repeat, label: "Recurring", href: "/recurring" },
  { icon: Wallet, label: "Budget", href: "/budget" },
  { icon: Users, label: "Transfers", href: "/transfers" },
  { icon: BarChart3, label: "Analytics", href: "/analytics" },  // REMOVE
  { icon: Settings, label: "Settings", href: "/settings" },
];

// PROPOSED NAV ITEMS
const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/" },
  { icon: ArrowLeftRight, label: "Transactions", href: "/transactions" },
  { icon: Upload, label: "Import", href: "/import" },
  { icon: Receipt, label: "Bills", href: "/bills" },           // RENAMED
  { icon: Repeat, label: "Subscriptions", href: "/subscriptions" }, // RENAMED
  { icon: Wallet, label: "Budget", href: "/budget" },
  { icon: Users, label: "Transfers", href: "/transfers" },
  { icon: Settings, label: "Settings", href: "/settings" },
];
```

### Dashboard Page
**File:** `apps/web/src/app/page.tsx`

Changes needed:
1. Add always-visible header with Net Worth, Monthly Summary, Health Score
2. Reduce tabs from 4 to 2 (Overview, Insights)
3. Merge content from Analytics page
4. Remove duplicate widgets

---

## Backend Changes Required

### 1. Implement Budget Progress Endpoint
**File:** `apps/backend/src/ledgerloop/api/routes/budgets.py`

```python
@router.get("/{budget_id}/progress")
def get_budget_progress(budget_id: str) -> BudgetProgress:
    """Calculate actual spending vs budget for each category."""
    # Implementation needed
```

### 2. Fix or Remove Overdue Bills
**Option A:** Implement next_date tracking in recurring_series
**Option B:** Remove overdue section from Calendar/Bills page

### 3. Wire Up P2P Service Filter
**File:** `apps/backend/src/ledgerloop/api/routes/p2p.py`
Add `service` query parameter to counterparties endpoint.

---

## Migration Steps

### Phase 1: Cleanup (No breaking changes)
1. Delete `/analytics/page.tsx`
2. Delete `/categories/page.tsx`
3. Delete `/rules/page.tsx`
4. Delete `/pulse/page.tsx`
5. Update Sidebar to remove Analytics link
6. Add redirects for old routes (optional)

### Phase 2: Dashboard Consolidation
1. Add always-visible header to Dashboard
2. Reduce tabs to 2 (Overview, Insights)
3. Merge Analytics content into Dashboard Insights tab
4. Remove redundant widgets

### Phase 3: Page Renames
1. Rename Calendar → Bills (route and all references)
2. Rename Recurring → Subscriptions (route and all references)
3. Update Sidebar navigation

### Phase 4: Backend Fixes
1. Implement `/api/budgets/{id}/progress`
2. Decide on overdue bills (fix or remove)
3. Wire up P2P service filter

### Phase 5: Polish
1. Add error boundaries to all dashboard cards
2. Standardize loading states (use CardSkeleton everywhere)
3. Fix type safety issues
4. Accessibility improvements

---

## Expected Outcomes

### Before
- 15 pages, 4 redundant
- 9 sidebar items
- Confusing duplicate routes
- Multiple broken features

### After
- 11 pages, 0 redundant
- 8 sidebar items
- Clear single path to each feature
- All features working

### User Benefits
1. **Faster navigation** - fewer clicks to find features
2. **Clearer mental model** - one place for each function
3. **Working features** - no more dead buttons
4. **Better performance** - fewer redundant API calls

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Users bookmarked old URLs | Add redirects: /analytics → /, /categories → /settings/categories |
| Breaking changes | Phase 1 is non-breaking, test thoroughly before Phase 2-3 |
| Lost features | Ensure all Analytics features preserved in Dashboard |

---

## Success Metrics

After restructure, verify:
- [ ] All 8 sidebar links work
- [ ] No 404 pages
- [ ] Dashboard loads < 2 seconds
- [ ] All action buttons are functional
- [ ] Budget progress shows actual data
- [ ] No TypeScript `any` warnings

---

*Proposal generated: 2025-12-27*
