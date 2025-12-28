# KASHAT PAGE INVENTORY

## Summary
- **Total Pages:** 12 (was 16, deleted 4 redundant)
- **Working:** 11
- **Partial/Issues:** 1 (Bills - overdue returns empty)
- **In Sidebar Navigation:** 9 (removed Analytics)
- **Not in Sidebar:** 3 (Settings sub-pages)

> **UPDATE 2025-12-28:**
> - Added Net Worth page with full asset/liability tracking backend
> - Added DashboardHeader component with always-visible key metrics (Net Worth, Cashflow, Savings Rate)
> - **DELETED** 4 redundant pages: /analytics, /categories, /rules, /pulse
> - **RENAMED** /calendar → /bills, /recurring → /subscriptions
> - Added redirects for deleted and renamed pages in next.config.js
> - **FIXED** Budget progress endpoint (GET /api/budgets/{id}/progress)
> - **REMOVED** Link Recurring stub from Transfers page

---

## Page List by Category

### Main Navigation Pages

#### 1. Dashboard (/)
**File:** `apps/web/src/app/page.tsx`
**Lines:** ~742
**Purpose:** AI-powered financial command center with comprehensive overview
**Status:** Working

**Header Component:** `DashboardHeader.tsx` - Always visible key metrics:
- Net Worth (clickable → /networth)
- This Month Cashflow (income - spending)
- Savings Rate (with color-coded thresholds)

**Tabs (4):**
| Tab | Icon | Components |
|-----|------|------------|
| Overview | LayoutGrid | NetWorthCard, CashflowSummaryCard, BudgetSummaryCard, HealthScoreCard, RunwayCard, UpcomingBillsCard, SpendingBehaviorCard, AIInsightsWidget, IntelligenceFeed, AnomalyAlerts, RecurringSummaryWidget |
| Spending | BarChart3 | 4 summary cards, SpendingChart, Top Merchants, Recurring Expenses |
| Trends | Sparkles | AI Spending Patterns, AI Trend Analysis, Predictive Patterns |
| Forecast | LineChart | Spending Forecast, Income Forecast, Cashflow Projection |

**API Hooks Used:** 11 hooks (useAnalyticsDashboard, useAnalyticsMerchants, useAnalyticsMonthly, useSpendingPatterns, useAITrends, useSpendingForecast, useRecurringAnalytics, useIncomeForecast, useCashflowForecast, usePredictivePatterns, useSpendingByType) + useCompleteNetWorth (header)

**Links OUT:**
- /networth (DashboardHeader - Net Worth card)
- /import (Import Data button)
- /transactions?uncategorized=true
- /recurring
- /transfers
- /settings/automation

---

#### 1b. Net Worth (/networth) - NEW
**File:** `apps/web/src/app/networth/page.tsx`
**Purpose:** Full asset and liability tracking for complete net worth picture
**Status:** Working

**Backend API Endpoints:**
- GET /api/assets - List all manual assets
- POST /api/assets - Create asset
- PUT /api/assets/{id} - Update asset
- DELETE /api/assets/{id} - Delete asset
- GET /api/assets/summary - Asset breakdown by type
- GET /api/liabilities - List all liabilities
- POST /api/liabilities - Create liability
- PUT /api/liabilities/{id} - Update liability
- DELETE /api/liabilities/{id} - Delete liability
- GET /api/networth/complete - Full net worth with bank accounts + assets + liabilities
- GET /api/metals/spot - Live precious metal prices
- POST /api/metals/refresh - Update all metal assets with current spot prices

**Asset Types Supported:**
- Real Estate (address, property type, purchase price)
- Vehicles (year/make/model, VIN)
- Precious Metals (gold, silver, platinum, palladium with live spot pricing)
- Investments (401k, IRA, brokerage, HSA, crypto)
- Business value (valuation method, revenue-based)
- Other assets

**Liability Types Supported:**
- Mortgage (linked to real estate asset)
- Auto Loan (linked to vehicle asset)
- Student Loan
- Personal Loan
- Credit Card
- Other

---

#### 2. Transactions (/transactions)
**File:** `apps/web/src/app/transactions/page.tsx`
**Purpose:** Browse, filter, and manage all transactions
**Status:** Working

**Features:**
- Search with debounce (500ms)
- Filter by: category, account, date range, type (all/uncategorized/income/business)
- Sort by date (descending)
- Pagination (10/20/50/100 per page)
- Bulk auto-categorize uncategorized transactions

**API Hooks Used:** useTransactions, useTransactionStats (x3), useCategories, useAccounts, useCategorizeAllTransactions, useCategorizationStatus, useCategoryCoverage, useDebounce

**Buttons:**
- Auto-Categorize (bulk AI categorization)
- Filter buttons (All, Uncategorized, Income, Business)
- Clear filters
- Pagination controls

---

#### 3. Import (/import)
**File:** `apps/web/src/app/import/page.tsx`
**Purpose:** Upload bank statements (CSV/PDF) and view import history
**Status:** Working

**Features:**
- Drag-and-drop file upload
- Multiple file selection
- Import history with status badges
- Reprocess/Delete import runs

**API Hooks Used:** useImportRuns, useBulkUpload, useDeleteImportRun, useReprocessImportRun

**Issues:**
- File size limit (50MB) not enforced in frontend
- No upload progress indicator
- Uses browser confirm() for delete

---

#### 4. Bills (/bills)
**File:** `apps/web/src/app/bills/page.tsx`
**Purpose:** View monthly calendar of upcoming bill due dates
**Status:** Partial (overdue endpoint returns empty)

**Features:**
- Monthly calendar grid
- Bill summary cards (7/30/90 days)
- Overdue bills alert (non-functional)
- Previous/Next/Today navigation

**API Hooks Used:** useCalendarMonth, useBillSummary, useUpcomingBills, useOverdueBills

**Issues:**
- Overdue endpoint returns [] always (backend limitation)
- Calendar is read-only (no interaction)
- Only shows 2 bills per day

---

#### 5. Subscriptions (/subscriptions)
**File:** `apps/web/src/app/subscriptions/page.tsx`
**Purpose:** Manage recurring payments and subscriptions
**Status:** Working

**Tabs (6):**
- All, Subscriptions, Housing & Utilities, Loans, Credit Cards, Insurance

**Features:**
- Pending review with bulk confirm/reject
- Run pattern detection
- Insights, optimizations, cancellation risks
- Upcoming payments (14 days)
- Spending breakdown by type

**API Hooks Used:** 13 hooks (useRecurringSuggestions, useConfirmedRecurring, useRecurringSummary, useSubscriptions, useBills, useLoans, useCreditCards, useInsurance, useRecurringInsights, useOptimizations, useCancellationRisks, useUpcomingPayments, useSpendingByType) + 3 mutations

---

#### 6. Budget (/budget)
**File:** `apps/web/src/app/budget/page.tsx`
**Purpose:** Create and track spending budgets
**Status:** Partial (missing progress endpoint)

**Features:**
- Budget list with progress bars
- Create new budget dialog
- Category-level limits (not fully implemented)

**API Hooks Used:** useBudgets, useBudgetProgress (MISSING ENDPOINT)

**Issues:**
- GET /api/budgets/{id}/progress endpoint doesn't exist
- Can only create budgets with empty categories
- No edit/update functionality

---

#### 7. Transfers (/transfers)
**File:** `apps/web/src/app/transfers/page.tsx`
**Purpose:** Track P2P transfers and manage counterparties
**Status:** Working

**Tabs (2):**
- People (counterparties)
- Internal Transfers

**Features:**
- Counterparty cards with filters
- Detect P2P transactions
- Enrich with AI
- Merge duplicates

**API Hooks Used:** useP2PStats, useCounterparties, useEnrichmentStats, useDetectP2P, useEnrichP2P, useMergeCounterparties

**Issues:**
- Service filter not implemented (UI shows but doesn't work)
- Link Recurring button is stub (console.log only)

---

#### 8. Settings (/settings)
**File:** `apps/web/src/app/settings/page.tsx`
**Lines:** ~1504
**Purpose:** Main settings hub
**Status:** Working

**Tabs (4):**
| Tab | Purpose |
|-----|---------|
| General | App preferences, recurring settings |
| AI | AI provider config, categorization settings |
| Dashboard | Dashboard preferences |
| Data | Export, backup, optimize, factory reset |

---

### Settings Sub-Pages

#### 9. Settings/Categories (/settings/categories)
**File:** `apps/web/src/app/settings/categories/page.tsx`
**Purpose:** Manage transaction categories
**Status:** Working

**Features:**
- Hierarchical category tree
- CRUD operations
- AI gap analysis
- Bootstrap standard categories

---

#### 10. Settings/Automation (/settings/automation)
**File:** `apps/web/src/app/settings/automation/page.tsx`
**Purpose:** Create automation rules for categorization
**Status:** Working

**Features:**
- Active rules table
- Quick create rule
- AI-suggested rules
- Apply all rules

---

#### 11. Settings/System (/settings/system)
**File:** `apps/web/src/app/settings/system/page.tsx`
**Purpose:** System monitoring and diagnostics
**Status:** Working (same as Pulse)

---

### Deleted Pages (redirects in place)

The following pages were **deleted** as redundant. Redirects are configured in `next.config.js`:

| Old Route | Redirects To | Reason |
|-----------|--------------|--------|
| /analytics | / (Dashboard) | 90% duplicate of Dashboard |
| /categories | /settings/categories | Exact duplicate |
| /rules | /settings/automation | Exact duplicate |
| /pulse | /settings/system | Exact duplicate |

---

## Navigation Map

```
Sidebar Navigation (9 items):
├── Dashboard (/)
├── Net Worth (/networth)           <-- NEW
├── Transactions (/transactions)
├── Import (/import)
├── Bills (/bills)                  <-- RENAMED from /calendar
├── Subscriptions (/subscriptions)  <-- RENAMED from /recurring
├── Budget (/budget)
├── Transfers (/transfers)
└── Settings (/settings)
    ├── /settings/categories
    ├── /settings/automation
    └── /settings/system

Redirects (deleted + renamed pages):
├── /analytics    → /
├── /categories   → /settings/categories
├── /rules        → /settings/automation
├── /pulse        → /settings/system
├── /calendar     → /bills
└── /recurring    → /subscriptions
```

---

## API Endpoints Used Across All Pages

| Endpoint | Method | Used By |
|----------|--------|---------|
| /api/networth | GET | Dashboard, NetWorthCard |
| /api/budgets | GET, POST | Dashboard, Budget |
| /api/budgets/{id}/progress | GET | Budget (MISSING) |
| /api/calendar/upcoming | GET | Dashboard, Calendar |
| /api/calendar/summary | GET | Dashboard, Calendar |
| /api/calendar/month/{y}/{m} | GET | Calendar |
| /api/calendar/overdue | GET | Calendar (returns []) |
| /api/transactions | GET | Transactions |
| /api/categories | GET, POST, PATCH, DELETE | Multiple |
| /api/accounts | GET | Transactions |
| /api/imports/runs | GET | Import, Pulse |
| /api/imports/bulk | POST | Import |
| /api/recurring/* | GET, POST | Recurring |
| /api/p2p/* | GET, POST | Transfers |
| /api/analytics/* | GET | Dashboard, Analytics |
| /api/intelligence/* | GET | Dashboard |
| /api/ai/* | GET, POST | Settings, Dashboard |
| /api/health | GET | Pulse, Settings |
