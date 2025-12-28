# KASHAT COMPONENT INVENTORY

## Summary
- **Total Components:** 44
- **Dashboard Components:** 11
- **Chart Components:** 3
- **Layout Components:** 4
- **UI Primitives (shadcn):** 19
- **Custom UI Components:** 7
- **Hooks:** 15

---

## Components by Category

### Dashboard Components (11)
Location: `apps/web/src/components/dashboard/`

| Component | File | Purpose | APIs Used | Used On |
|-----------|------|---------|-----------|---------|
| NetWorthCard | NetWorthCard.tsx | Display net worth, assets, liabilities | GET /api/networth | Dashboard Overview |
| CashflowSummaryCard | CashflowSummaryCard.tsx | Income, spending, savings rate | useAnalyticsSummary | Dashboard Overview |
| BudgetSummaryCard | BudgetSummaryCard.tsx | Budget progress overview | useBudgets | Dashboard Overview |
| HealthScoreCard | HealthScoreCard.tsx | Financial health score (A-F) | useFinancialHealth | Dashboard Overview |
| RunwayCard | RunwayCard.tsx | Cash runway projection | useCashflowProjection | Dashboard Overview |
| UpcomingBillsCard | UpcomingBillsCard.tsx | Bills due in 7 days | useUpcomingBills, useBillSummary | Dashboard Overview |
| SpendingBehaviorCard | SpendingBehaviorCard.tsx | Spending persona analysis | useSpendingBehavior | Dashboard Overview |
| AIInsightsWidget | AIInsightsWidget.tsx | AI metrics and insights | useInsights, useCategoryCoverage, useAISuccessMetrics, useRuleSuggestions | Dashboard Overview |
| IntelligenceFeed | IntelligenceFeed.tsx | Intelligence items feed | useIntelligenceFeed | Dashboard Overview |
| AnomalyAlerts | AnomalyAlerts.tsx | Anomaly detection alerts | useAnomalies | Dashboard Overview |
| RecurringSummaryWidget | RecurringSummaryWidget.tsx | Recurring summary | useRecurringSummary, useUpcomingPayments, useOptimizations | Dashboard Overview |

### Chart Components (3)
Location: `apps/web/src/components/charts/`

| Component | File | Purpose | Used On |
|-----------|------|---------|---------|
| SpendingChart | SpendingChart.tsx | Line chart for income vs spending | Dashboard Spending, Analytics |
| CategoryPieChart | CategoryPieChart.tsx | Pie chart for spending by category | Analytics |
| MonthlyBarChart | MonthlyBarChart.tsx | Bar chart for monthly trends | Analytics |

### Layout Components (4)
Location: `apps/web/src/components/layout/`

| Component | File | Purpose |
|-----------|------|---------|
| Sidebar | Sidebar.tsx | Main navigation sidebar (9 items) |
| BottomNav | BottomNav.tsx | Mobile bottom navigation |
| MobileNav | MobileNav.tsx | Mobile hamburger menu |
| CommandPalette | CommandPalette.tsx | Cmd+K search palette |

### Custom UI Components (7)
Location: `apps/web/src/components/ui/`

| Component | File | Purpose |
|-----------|------|---------|
| Amount | Amount.tsx | Currency display with formatting |
| AnimatedNumber | AnimatedNumber.tsx | Animated number transitions |
| EmptyState | EmptyState.tsx | Empty state display |
| ErrorBoundary | ErrorBoundary.tsx | Error boundary wrapper |
| LoadingSpinner | LoadingSpinner.tsx | Loading states, CardSkeleton |
| ThemeToggle | ThemeToggle.tsx | Dark/light mode toggle |
| Toaster | Toaster.tsx | Toast notifications (sonner) |

### UI Primitives - shadcn (19)
Location: `apps/web/src/components/ui/`

| Component | File |
|-----------|------|
| alert | alert.tsx |
| badge | badge.tsx |
| button | button.tsx |
| card | card.tsx |
| checkbox | checkbox.tsx |
| command | command.tsx |
| dialog | dialog.tsx |
| dropdown-menu | dropdown-menu.tsx |
| input | input.tsx |
| label | label.tsx |
| progress | progress.tsx |
| select | select.tsx |
| separator | separator.tsx |
| sheet | sheet.tsx |
| slider | slider.tsx |
| switch | switch.tsx |
| table | table.tsx |
| tabs | tabs.tsx |

### Providers (1)
| Component | File | Purpose |
|-----------|------|---------|
| providers | providers.tsx | QueryClient, ThemeProvider |

---

## Hooks Inventory (15)
Location: `apps/web/src/hooks/`

| Hook | File | Purpose | Endpoints |
|------|------|---------|-----------|
| useAIQueue | useAIQueue.ts | AI job queue management | /api/ai/queue/* |
| useAccounts | useAccounts.ts | Account data | /api/accounts |
| useAnalytics | useAnalytics.ts | All analytics hooks | /api/analytics/* |
| useAutomation | useAutomation.ts | Rules and automation | /api/rules/* |
| useCategories | useCategories.ts | Category CRUD | /api/categories/* |
| useDebounce | useDebounce.ts | Debounce utility | - |
| useImports | useImports.ts | Import operations | /api/imports/* |
| useIntelligence | useIntelligence.ts | Intelligence feed | /api/intelligence/* |
| useKeyboardShortcuts | useKeyboardShortcuts.ts | Keyboard shortcuts | - |
| useMutationToast | useMutationToast.ts | Toast notifications | - |
| useP2P | useP2P.ts | P2P/transfers | /api/p2p/* |
| usePulse | usePulse.ts | System health | /api/health/* |
| useRecurring | useRecurring.ts | Recurring payments | /api/recurring/* |
| useSettings | useSettings.ts | App settings | /api/settings/* |
| useTransactions | useTransactions.ts | Transactions | /api/transactions/* |

---

## Component Reuse Analysis

### Used on Multiple Pages (Good)
| Component | Pages Used | Usage Count |
|-----------|------------|-------------|
| Card | All pages | 15+ |
| Button | All pages | 15+ |
| Badge | Most pages | 10+ |
| LoadingSpinner | Most pages | 10+ |
| Table | Transactions, Recurring, Settings | 3 |
| Tabs | Dashboard, Recurring, Transfers, Settings | 4 |
| SpendingChart | Dashboard, Analytics | 2 |

### Only Used Once (Consider Inlining)
| Component | Page Used |
|-----------|-----------|
| CategoryPieChart | Analytics |
| MonthlyBarChart | Analytics |
| CommandPalette | Layout (global) |

### Potentially Dead Code
| Component | File | Notes |
|-----------|------|-------|
| BottomNav | layout/BottomNav.tsx | Check if actually rendered |
| MobileNav | layout/MobileNav.tsx | Check if actually rendered |
| EmptyState | ui/EmptyState.tsx | Verify usage |

---

## Component Dependencies

### Dashboard Component Dependencies
```
Dashboard Page
├── NetWorthCard
│   └── AnimatedNumber (AnimatedCurrency)
├── CashflowSummaryCard
│   └── AnimatedNumber
├── BudgetSummaryCard
│   └── Progress
├── HealthScoreCard
│   └── AnimatedNumber
├── RunwayCard
│   └── Progress
├── UpcomingBillsCard
├── SpendingBehaviorCard
├── AIInsightsWidget
│   └── Progress
├── IntelligenceFeed
├── AnomalyAlerts
└── RecurringSummaryWidget
```

### Chart Library Usage
All charts use **Recharts**:
- LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
- PieChart, Pie, Cell
- BarChart, Bar

---

## Component Health Issues

### Missing Error Boundaries
These components don't handle errors gracefully:
- All dashboard cards (would break entire dashboard if one fails)
- Chart components
- Data tables

### Type Safety Issues
Components using `any` types:
- Dashboard page (line 342, merchant: any)
- Transactions page (multiple any casts)
- Analytics page (heavy any usage)
- All settings pages

### Loading State Inconsistencies
| Component | Loading State |
|-----------|---------------|
| NetWorthCard | CardSkeleton |
| Others | Loader2 spinner |

Recommendation: Standardize on CardSkeleton for cards

### Missing Accessibility
- Date inputs lack labels
- Some icons missing aria-labels
- Tree structures use divs instead of semantic markup
