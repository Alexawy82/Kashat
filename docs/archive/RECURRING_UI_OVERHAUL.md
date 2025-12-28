# LedgerLoop Recurring UI Overhaul - Complete Design Specification

> **Created:** December 24, 2024
> **Status:** Design Complete - Ready for Implementation
> **Current Usage:** ~5 of 38 endpoints
> **Target Usage:** 30+ endpoints (100% of backend power)

---

## Executive Summary

This document outlines a comprehensive overhaul of the Recurring page to leverage 100% of the backend capabilities. The redesign covers ALL recurring payment types (housing, utilities, subscriptions, loans, credit cards, insurance), provides drill-down capabilities, reports, mark-as-paid functionality, and AI-powered insights.

---

## Current State vs Target State

| Metric | Current | Target |
|--------|---------|--------|
| Endpoints Used | ~5 | 30+ |
| Types Displayed | 2 (utilities, subscriptions) | 6+ (housing, subs, loans, cards, insurance, other) |
| Insights | None | AI-powered savings, risks, forecasts |
| Actions | Confirm/Reject | Confirm, Reject, Mark Paid, Pause, Cancel, Skip, Edit |
| Reports | None | Trends, Savings, Upcoming, Export |
| Learning | None | Feedback loop to train AI |

---

## Complete Type Taxonomy

```
RECURRING TYPES
├── 🏠 Housing & Utilities (bill)
│   ├── Rent
│   ├── Mortgage
│   ├── HOA
│   ├── Property Tax
│   ├── Electric
│   ├── Gas
│   ├── Water
│   ├── Sewage
│   ├── Trash
│   ├── Internet
│   ├── Cable
│   └── Phone
│
├── 📺 Subscriptions (subscription)
│   ├── Streaming Video (Netflix, Hulu, Disney+, HBO, etc.)
│   ├── Streaming Music (Spotify, Apple Music, etc.)
│   ├── Cloud Storage (iCloud, Google One, Dropbox)
│   ├── Software (Adobe, Microsoft 365, etc.)
│   ├── AI Services (ChatGPT, Claude, etc.)
│   ├── Gaming (Xbox, PlayStation, Nintendo)
│   ├── Fitness (Gym, Peloton, etc.)
│   ├── Wellness (Calm, Headspace, etc.)
│   ├── News & Media (NYT, WSJ, etc.)
│   ├── Creator Platforms (Patreon, YouTube Premium)
│   ├── Membership (Costco, Amazon Prime)
│   ├── Identity Protection (LifeLock, etc.)
│   ├── FinTech (Robinhood Gold, etc.)
│   ├── Education (Coursera, Skillshare, etc.)
│   └── Pet Services (BarkBox, etc.)
│
├── 💳 Loans & Debt (loan)
│   ├── Mortgage
│   ├── Auto Loan
│   ├── Motorcycle/Boat/RV Loan
│   ├── Personal Loan
│   ├── Student Loan
│   ├── BNPL (Affirm, Klarna, Afterpay)
│   └── Other Loan
│
├── 🏦 Credit Cards (credit_card)
│   ├── Chase
│   ├── Amex
│   ├── Capital One
│   ├── Citi
│   ├── Discover
│   └── Other
│
└── 🛡️ Insurance (insurance)
    ├── Auto Insurance
    ├── Home Insurance
    ├── Renters Insurance
    ├── Life Insurance
    ├── Health Insurance
    ├── Pet Insurance
    └── Other Insurance
```

---

## Complete API Endpoints Reference

### Core Operations (5 endpoints)

| Method | Endpoint | Purpose | Returns |
|--------|----------|---------|---------|
| POST | /recurring/suggest | Run detection algorithm | {candidates: [], total} |
| GET | /recurring | List all series | Array of enriched series |
| GET | /recurring/pending | List pending series | Pending series |
| GET | /recurring/confirmed | List confirmed series | Confirmed series |
| GET | /recurring/{series_id}/transactions | Get transaction history | [{date, amount}] for sparklines |

### Confirmation Actions (4 endpoints)

| Method | Endpoint | Purpose | Returns |
|--------|----------|---------|---------|
| POST | /recurring/confirm | Confirm series | Confirmation result |
| POST | /recurring/reject | Reject series | Rejection result |
| POST | /recurring/confirm/{series_id}/with-learning | Confirm + train AI | Confirms AND records feedback |
| POST | /recurring/reject/{series_id}/with-learning | Reject + train AI | Rejects AND records feedback |

### Type-Filtered Lists (8 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /recurring/subscriptions | Streaming, software, memberships |
| GET | /recurring/bills | Utilities, insurance, rent |
| GET | /recurring/loans | Auto, mortgage, personal, student |
| GET | /recurring/credit-cards | Credit card payments |
| GET | /recurring/insurance | Auto, home, health, life, pet |
| GET | /recurring/essential | All essential (must-pay) charges |
| GET | /recurring/discretionary | All optional/cancellable charges |
| GET | /recurring/by-type/{type} | Generic type filter |

### Summary & Analytics (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /recurring/summary | Complete breakdown by type |
| GET | /recurring/insights/spending-by-type | Spending totals by type |

### Data Maintenance (3 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /recurring/reclassify | Re-run pattern classifier |
| POST | /recurring/merge-duplicates | Deduplicate merchants |
| POST | /recurring/reclassify-with-llm | LLM classification for unknowns |

### LLM Intelligence (3 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /recurring/intelligence/analyze | Analyze single description |
| GET | /recurring/intelligence/cache-stats | Cache statistics |
| POST | /recurring/intelligence/cleanup-cache | Remove old cache |

### Insights Engine (5 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /recurring/insights | Natural language insights |
| GET | /recurring/insights/upcoming | Upcoming payments (days param) |
| GET | /recurring/insights/cash-flow | Cash flow forecast (months param) |
| GET | /recurring/insights/cancellation-risks | Cancellation risk analysis |
| GET | /recurring/insights/optimizations | Savings suggestions |

### AI Workflow & Learning (6 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /recurring/ai-workflow/feedback | Submit correction feedback |
| GET | /recurring/ai-workflow/stats | Learning system stats |
| POST | /recurring/ai-workflow/review | AI review single series |
| POST | /recurring/ai-workflow/batch-review | Batch review pending |
| POST | /recurring/ai-workflow/backfill-memory | Bootstrap learning |
| GET | /recurring/ai-workflow/accuracy | Accuracy by type |

**Total: 38 Recurring Endpoints**

---

## Master Page Layout

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Recurring Payments                                        [⚙️ Settings] [📊 Report]│
│ Track, manage, and optimize all your recurring charges                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │  $4,234.56  │ │  $2,890.00  │ │  $1,344.56  │ │  $50,814.72 │ │  12 / 47    │ │
│ │   Monthly   │ │  Essential  │ │Discretionary│ │   Annual    │ │  Pending    │ │
│ │   ▲ 2.3%    │ │   ▼ 1.1%   │ │   ▲ 5.2%   │ │   ▲ 2.3%   │ │  Review     │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
│                                                                                 │
├──────────────────────────────────────────────── ALERTS ────────────────────────┤
│ 🔴 3 Overdue: Duke Energy ($89), Spectrum ($65), Car Insurance ($107) = $261   │
│ 🟡 5 Due This Week: Netflix, Spotify, Mortgage, Student Loan, Gym = $1,847     │
│ 🟠 2 Price Hikes: YouTube Premium (+$2), Adobe CC (+$5) = +$84/year            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                             AI INSIGHTS                               [See All] │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ 💰 SAVINGS  │ │ ⚠️ CANCEL?  │ │ 📉 DOWNGRADE│ │ 💡 BUNDLE   │ │ 📞 NEGOTIATE│ │
│ │ 3 streaming │ │ Paramount+  │ │ iCloud 2TB  │ │ Insurance   │ │ Spectrum    │ │
│ │ services    │ │ No activity │ │ Using 20GB  │ │ Auto+Home   │ │ Save $20/mo │ │
│ │ Save $240/yr│ │ Save $156/yr│ │ Save $60/yr │ │ Save $180/yr│ │ Save $240/yr│ │
│ │ [Review]    │ │ [Cancel]    │ │ [Downgrade] │ │ [Compare]   │ │ [Call Script│ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ⏳ PENDING REVIEW (12 patterns detected)                    [Confirm All] [Skip]│
│ ┌───────────────────────────────────────────────────────────────────────────────┤
│ │ ☑ │ Merchant          │ Type          │ Cadence  │ Amount    │ Conf │ Action │
│ ├───┼───────────────────┼───────────────┼──────────┼───────────┼──────┼────────┤
│ │ ☑ │ 📺 Netflix        │ Streaming     │ Monthly  │ $15.99    │ 95%  │ ✓  ✗  │
│ │ ☑ │ 🎵 Spotify        │ Music         │ Monthly  │ $10.99    │ 92%  │ ✓  ✗  │
│ │ ☐ │ ❓ CHECKCARD 1234 │ Unknown       │ Monthly  │ $29.99    │ 45%  │ ✓  ✗  │
│ │   │   └─ AI suggests: Software subscription                   │ [Identify]  │
│ └───────────────────────────────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│ [All] [🏠 Housing $1,890] [📺 Subs $456] [💳 Loans $1,200] [🏦 Cards $580] [🛡️ Ins $108]│
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         🏠 HOUSING & UTILITIES                                  │
│                              $1,890.34/mo                                       │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ ESSENTIAL (Must Pay)                                                        │ │
│ │ ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ 🏠 Mortgage         Wells Fargo          $1,200.00  Monthly   Jan 1     │ │ │
│ │ │    └─ Principal: $180k remaining • 23 years left • 4.5% APR             │ │ │
│ │ │    ▁▂▂▂▂▂▂▂▂▂▂▂ (stable)            [Mark Paid] [View History] [•••]   │ │ │
│ │ └─────────────────────────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ ⚡ Duke Energy      Electric             $89.23 ~   Monthly   Jan 15    │ │ │
│ │ │    └─ Variable: $65-$142 range • Summer peak                   🔴 3d late│ │ │
│ │ │    ▂▃▅▇▅▃▂▂▃▅▇▅ (seasonal)          [Mark Paid] [View History] [•••]   │ │ │
│ │ └─────────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│ [Continue with more sections...]                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Section Details

### 1. Command Bar (Summary Strip)

**Endpoints Used:**
- `GET /recurring/summary` → `{total_monthly, essential_monthly, discretionary_monthly, total_annual}`

**Components:**
- Monthly total with trend indicator
- Essential vs Discretionary split
- Annual projection
- Pending review count
- Action buttons (Reports, Detect)

### 2. Alerts Banner

**Endpoints Used:**
- `GET /recurring/insights/upcoming?days=7`
- `GET /recurring` with status filter for overdue

**Displays:**
- Overdue payments (red)
- Due this week (yellow)
- Price hikes detected (orange)

### 3. AI Insights Carousel

**Endpoints Used:**
- `GET /recurring/insights?limit=10`
- `GET /recurring/insights/optimizations?limit=5`
- `GET /recurring/insights/cancellation-risks?limit=5`

**Card Types:**
- Savings opportunities
- Cancellation candidates
- Downgrade suggestions
- Bundle recommendations
- Negotiation opportunities

### 4. Pending Review Section

**Endpoints Used:**
- `GET /recurring/pending`
- `POST /recurring/confirm/{id}/with-learning`
- `POST /recurring/reject/{id}/with-learning`
- `GET /recurring/{series_id}/transactions`

**Features:**
- Bulk selection and actions
- Confidence indicator
- AI classification suggestions
- Sparkline preview
- Individual confirm/reject

### 5. Type-Based Tabs

**Endpoints Used:**
- `GET /recurring/bills`
- `GET /recurring/subscriptions`
- `GET /recurring/loans`
- `GET /recurring/credit-cards`
- `GET /recurring/insurance`
- `GET /recurring/insights/spending-by-type`

**Each Tab Shows:**
- Type total (monthly)
- Grouped by sub-category
- Essential vs Discretionary sections
- Individual series cards with:
  - Merchant name
  - Amount and cadence
  - Next due date
  - Status badge
  - Sparkline
  - Quick actions

### 6. Series Card (Enhanced)

**Data Displayed:**
- Merchant name (AI-extracted)
- Amount with variability indicator (~)
- Cadence (Weekly/Monthly/Annual)
- Next due date
- Status (Active/Overdue/Cancelled)
- Sparkline (12-month history)
- Price hike indicator
- Loan progress bar (for loans)
- Essential badge

**Actions:**
- Mark Paid
- View History
- Edit
- Pause
- Cancel
- Correct Classification

### 7. Upcoming Calendar

**Endpoints Used:**
- `GET /recurring/insights/upcoming?days=14`

**Layout:**
- Today column
- Tomorrow column
- Next 5 days grouped
- Total amounts per period

### 8. Cash Flow Forecast

**Endpoints Used:**
- `GET /recurring/insights/cash-flow?months=6`

**Displays:**
- Monthly income projection
- Monthly recurring expenses
- Net cash flow
- Risk level indicator
- Visual bar chart

### 9. Annual Summary

**Data:**
- Pie chart by type
- Total annual spend
- Essential vs Discretionary breakdown
- Savings target indicator

---

## Drill-Down Modal (Series Detail View)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 📺 Netflix                                                              [✕]    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Status: ✅ Active            Type: 📺 Streaming Video                         │
│  Amount: $15.99/mo            Cadence: Monthly                                  │
│  Next Due: Jan 15, 2025       Essential: No                                     │
│  Annual Cost: $191.88                                                           │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  PAYMENT HISTORY                                                    [Export CSV]│
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ▁▁▁▁▁▁▁▁▁▁▂▂▂▂▂▂▂▂▂▂▂▂▂▂                                               │  │
│  │  $13.99 ────────────────── $15.99 (current)                              │  │
│  │                     ↑ Price increased Nov 2024                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  │ Date       │ Amount  │ Status    │ Account              │                   │
│  │────────────│─────────│───────────│──────────────────────│                   │
│  │ Dec 15, 24 │ $15.99  │ ✓ Paid    │ Chase Sapphire ****1234                  │
│  │ Nov 15, 24 │ $15.99  │ ✓ Paid    │ Chase Sapphire ****1234 │ 🟠 Price hike  │
│  │ Oct 15, 24 │ $13.99  │ ✓ Paid    │ Chase Sapphire ****1234                  │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ACTIONS                                                                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │ Mark Paid  │ │ Skip Next  │ │ Pause      │ │ Cancel     │ │ Edit       │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  CLASSIFICATION                                      [Correct This]            │
│  Type: Subscription → Streaming Video                                           │
│  Essential: No (discretionary)                                                  │
│  AI Confidence: 98%                                                             │
│                                                                                 │
│  ┌─ Correct Classification ─────────────────────────────────────────────────┐  │
│  │ Type: [Subscription ▼]  Sub-Category: [Streaming Video ▼]                │  │
│  │ Essential: [ ] Yes, this is a must-pay                                   │  │
│  │                                                        [Save & Train AI] │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Reports Modal

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 📊 Recurring Reports                                                    [✕]    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  [Summary] [By Type] [Trends] [Savings] [Upcoming] [History]                    │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              TRENDS TAB                                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Monthly Recurring Trend (12 months)                                      │  │
│  │                                                                           │  │
│  │  $4,400 ┤                                              ╭──────            │  │
│  │  $4,200 ┤                              ╭───────────────╯                  │  │
│  │  $4,000 ┤          ╭───────────────────╯                                  │  │
│  │  $3,800 ┤──────────╯                                                      │  │
│  │         └─────────────────────────────────────────────────────────        │  │
│  │          Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec       │  │
│  │                                                                           │  │
│  │  📈 +$234/mo (+5.8%) over 12 months                                       │  │
│  │  Biggest increases: Adobe CC (+$5), Netflix (+$2), Internet (+$10)        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  PRICE CHANGES (Last 12 Months)                                                 │
│  │ Service          │ Old      │ New      │ Change   │ Annual Impact │         │
│  │──────────────────│──────────│──────────│──────────│───────────────│         │
│  │ 🟠 Spectrum       │ $55.00   │ $65.00   │ +$10.00  │ +$120.00/yr   │         │
│  │ 🟠 Adobe CC       │ $49.99   │ $54.99   │ +$5.00   │ +$60.00/yr    │         │
│  │ 🟠 Netflix        │ $13.99   │ $15.99   │ +$2.00   │ +$24.00/yr    │         │
│  │ 🟢 Gym (negotiated)│ $59.99  │ $49.99   │ -$10.00  │ -$120.00/yr   │         │
│                                                                                 │
│  [Export PDF] [Export CSV] [Share]                                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Settings Page Integration

Add to Settings → Recurring & Detection:

### Detection Settings
- Amount Tolerance (slider 1-20%)
- Minimum Occurrences (slider 2-12)
- Include Weekly Patterns (toggle)
- Auto-Detect on Import (toggle)

### Display Preferences
- Default View (dropdown: All, By Type, By Due Date, Essential First)
- Show Annual Costs (toggle)
- Sparkline Period (dropdown: 6/12/24 months)

### AI & Learning
- Merchant Memory stats (count, accuracy)
- Recent learned patterns
- Backfill from History button
- Clear Memory button
- Export Patterns button
- Accuracy by Type table

### Maintenance
- Reclassify All button
- Merge Duplicates button
- Reclassify with LLM button
- Clean Intelligence Cache button

### Notifications (Future)
- Overdue Alerts toggle
- Price Increase Alerts toggle
- Upcoming Payment Reminders toggle
- Cancellation Suggestions toggle

---

## New Hooks Required

```typescript
// hooks/useRecurring.ts - COMPLETE REWRITE

// ===== SUMMARY & ANALYTICS =====
export const useRecurringSummary = () =>
  useQuery({
    queryKey: ['recurring', 'summary'],
    queryFn: () => api.get('/api/recurring/summary'),
    staleTime: 60_000,
  })

export const useSpendingByType = () =>
  useQuery({
    queryKey: ['recurring', 'spending-by-type'],
    queryFn: () => api.get('/api/recurring/insights/spending-by-type'),
  })

// ===== TYPE-FILTERED LISTS =====
export const useRecurringByType = (type: RecurringType) =>
  useQuery({
    queryKey: ['recurring', 'by-type', type],
    queryFn: () => api.get(`/api/recurring/${type}`),
  })

export const useSubscriptions = () => useRecurringByType('subscriptions')
export const useBills = () => useRecurringByType('bills')
export const useLoans = () => useRecurringByType('loans')
export const useCreditCards = () => useRecurringByType('credit-cards')
export const useInsurance = () => useRecurringByType('insurance')
export const useEssential = () => useRecurringByType('essential')
export const useDiscretionary = () => useRecurringByType('discretionary')

// ===== SERIES DETAIL & HISTORY =====
export const useSeriesTransactions = (seriesId: string, limit = 24) =>
  useQuery({
    queryKey: ['recurring', seriesId, 'transactions'],
    queryFn: () => api.get(`/api/recurring/${seriesId}/transactions?limit=${limit}`),
    enabled: !!seriesId,
  })

// ===== INSIGHTS =====
export const useRecurringInsights = (limit = 10) =>
  useQuery({
    queryKey: ['recurring', 'insights', limit],
    queryFn: () => api.get(`/api/recurring/insights?limit=${limit}`),
  })

export const useUpcomingPayments = (days = 14) =>
  useQuery({
    queryKey: ['recurring', 'upcoming', days],
    queryFn: () => api.get(`/api/recurring/insights/upcoming?days=${days}`),
  })

export const useCashFlowForecast = (months = 6) =>
  useQuery({
    queryKey: ['recurring', 'cash-flow', months],
    queryFn: () => api.get(`/api/recurring/insights/cash-flow?months=${months}`),
  })

export const useCancellationRisks = (limit = 20) =>
  useQuery({
    queryKey: ['recurring', 'cancellation-risks', limit],
    queryFn: () => api.get(`/api/recurring/insights/cancellation-risks?limit=${limit}`),
  })

export const useOptimizations = (limit = 10) =>
  useQuery({
    queryKey: ['recurring', 'optimizations', limit],
    queryFn: () => api.get(`/api/recurring/insights/optimizations?limit=${limit}`),
  })

// ===== ACTIONS =====
export const useConfirmWithLearning = () =>
  useMutation({
    mutationFn: (seriesId: string) =>
      api.post(`/api/recurring/confirm/${seriesId}/with-learning`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useRejectWithLearning = () =>
  useMutation({
    mutationFn: ({ seriesId, reason }: { seriesId: string; reason?: string }) =>
      api.post(`/api/recurring/reject/${seriesId}/with-learning`, { reason }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useMarkAsPaid = () =>
  useMutation({
    mutationFn: (seriesId: string) =>
      api.post(`/api/recurring/${seriesId}/mark-paid`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useUpdateSeries = () =>
  useMutation({
    mutationFn: ({ seriesId, updates }: { seriesId: string; updates: SeriesUpdate }) =>
      api.patch(`/api/recurring/${seriesId}`, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

// ===== AI FEEDBACK & LEARNING =====
export const useSubmitFeedback = () =>
  useMutation({
    mutationFn: (feedback: RecurringFeedback) =>
      api.post('/api/recurring/ai-workflow/feedback', feedback),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useAIWorkflowStats = () =>
  useQuery({
    queryKey: ['recurring', 'ai-stats'],
    queryFn: () => api.get('/api/recurring/ai-workflow/stats'),
  })

export const useAIAccuracy = () =>
  useQuery({
    queryKey: ['recurring', 'ai-accuracy'],
    queryFn: () => api.get('/api/recurring/ai-workflow/accuracy'),
  })

// ===== MAINTENANCE =====
export const useReclassify = () =>
  useMutation({
    mutationFn: () => api.post('/api/recurring/reclassify'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useMergeDuplicates = () =>
  useMutation({
    mutationFn: () => api.post('/api/recurring/merge-duplicates'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useReclassifyWithLLM = (limit = 100) =>
  useMutation({
    mutationFn: () => api.post(`/api/recurring/reclassify-with-llm?limit=${limit}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  })

export const useBackfillMemory = () =>
  useMutation({
    mutationFn: () => api.post('/api/recurring/ai-workflow/backfill-memory'),
  })

export const useIntelligenceCacheStats = () =>
  useQuery({
    queryKey: ['recurring', 'intelligence-cache'],
    queryFn: () => api.get('/api/recurring/intelligence/cache-stats'),
  })
```

---

## Backend Endpoints Needed (New)

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `POST /recurring/{id}/mark-paid` | Record manual payment | High |
| `PATCH /recurring/{id}` | Update series (essential, type, etc.) | High |
| `POST /recurring/{id}/skip-next` | Skip upcoming payment | Medium |
| `POST /recurring/{id}/pause` | Pause tracking | Medium |
| `POST /recurring/{id}/cancel` | Mark as cancelled | Medium |
| `GET /recurring/report/trends` | 12-month trend data | Medium |
| `GET /recurring/export` | Export CSV/PDF | Low |

---

## Implementation Phases

| Phase | Features | Effort | Value |
|-------|----------|--------|-------|
| **1** | Summary bar + Type tabs + All categories | 3 days | ★★★★★ |
| **2** | Series drill-down modal + Payment history | 2 days | ★★★★☆ |
| **3** | Insights carousel + Cancellation risks | 2 days | ★★★★★ |
| **4** | Upcoming calendar + Cash flow forecast | 1 day | ★★★★☆ |
| **5** | Mark paid + Actions (pause, cancel, skip) | 2 days | ★★★★★ |
| **6** | Reports modal + Export | 2 days | ★★★☆☆ |
| **7** | Settings integration + AI learning UI | 1 day | ★★★☆☆ |
| **8** | Cross-page widgets (Dashboard, Analytics) | 1 day | ★★★★☆ |

---

## Cross-Page Integration

### Dashboard Widget
```tsx
<RecurringSummaryWidget>
  <StatCard label="Monthly Recurring" value={summary.total_monthly} />
  <UpcomingPayments items={upcoming.slice(0, 3)} />
  <SavingsOpportunity insight={topOptimization} />
</RecurringSummaryWidget>
```

### Analytics Integration
- Recurring vs One-Time spending chart
- Recurring trends over time
- Spending by recurring type pie chart

### Transactions Integration
- Badge showing recurring series name
- Link to series detail modal

---

## Key User Value Propositions

| Before | After |
|--------|-------|
| "I see my subscriptions" | "I see ALL recurring - mortgage, loans, utilities, subs, cards, insurance" |
| "Netflix is $15.99" | "Netflix is $15.99/mo ($192/yr), increased +$2 in Nov, paid via Chase" |
| "I have 23 recurring" | "23 recurring = $4,234/mo = $50,808/yr (75% essential, 25% discretionary)" |
| "When is this due?" | "3 overdue ($261), 5 due this week ($1,847), calendar view of next 14 days" |
| "Can I save money?" | "AI found 5 savings: cancel Paramount+ ($156/yr), negotiate Spectrum ($240/yr)" |
| "Is this a loan or subscription?" | "AI classified + you can correct it to train the system" |
| "Did I pay this?" | "Click 'Mark Paid' to track, view full payment history with sparkline" |

---

## File Structure (New/Modified)

```
apps/web/src/
├── app/recurring/
│   ├── page.tsx                    # Main page (complete rewrite)
│   ├── components/
│   │   ├── CommandBar.tsx          # Summary strip
│   │   ├── AlertsBanner.tsx        # Overdue/upcoming/price hikes
│   │   ├── InsightsCarousel.tsx    # AI insights cards
│   │   ├── PendingReview.tsx       # Pending patterns table
│   │   ├── TypeTabs.tsx            # Tab container
│   │   ├── SeriesCard.tsx          # Individual series display
│   │   ├── SeriesDetailModal.tsx   # Drill-down modal
│   │   ├── UpcomingCalendar.tsx    # Next 14 days view
│   │   ├── CashFlowForecast.tsx    # Monthly projection
│   │   ├── AnnualSummary.tsx       # Yearly breakdown
│   │   ├── ReportsModal.tsx        # Reports dialog
│   │   └── Sparkline.tsx           # Mini chart component
│   └── hooks/
│       └── useRecurringPage.ts     # Page-specific state
├── hooks/
│   └── useRecurring.ts             # Complete rewrite with all hooks
└── app/settings/
    └── recurring/
        └── page.tsx                # Recurring settings section
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Endpoints utilized | 30+ of 38 |
| Types displayed | All 6 categories |
| User actions available | 8+ (confirm, reject, mark paid, pause, cancel, skip, edit, correct) |
| Insights surfaced | Savings, risks, forecasts, upcoming |
| Learning enabled | Feedback → AI improvement |
| Export options | CSV, PDF |

---

## Next Steps

1. **Review and approve this design**
2. **Start Phase 1 implementation** (Summary bar + Type tabs)
3. **Iterate based on feedback**
4. **Complete remaining phases**

---

*This document serves as the complete specification for the Recurring UI overhaul. All implementation should reference this document for design decisions and component specifications.*
