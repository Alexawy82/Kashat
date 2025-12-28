# Recurring Page UI Overhaul Plan

> **Context:** This is ONE page within LedgerLoop. Not a full app - stay focused on delivering maximum value through our existing backend capabilities.

---

## Design Research

### Best Practices Applied

| Principle | Source | How We Apply |
|-----------|--------|--------------|
| Progressive Disclosure | [Bizbot](https://www.bizbot.com/blog/subscription-management-ux-10-design-tips/) | Show summary first, drill-down for details |
| F/Z Scanning Pattern | [Justinmind](https://www.justinmind.com/ui-design/dashboard-design-best-practices-ux) | Key metrics top-left, actions on right |
| Movable Widgets | [AntStack](https://www.antstack.com/blog/building-customizable-dashboard-widgets-using-react-grid-layout/) | Use `react-grid-layout` for customizable layout |
| Clean Dashboard | [Subskeep Case Study](https://vivishin.medium.com/designing-a-subscription-management-app-subskeep-a-ux-case-study-7e5adbc6e5e8) | Overview → Categories → Insights flow |

---

## Value We Deliver

| User Need | Widget/Section | Backend Endpoint |
|-----------|----------------|------------------|
| "What am I spending?" | **Summary Metrics** | `GET /recurring/summary` |
| "Break it down by type" | **Category Cards** | `GET /subscriptions`, `/bills`, `/loans` |
| "What's due soon?" | **Upcoming Widget** | `GET /insights/upcoming?days=14` |
| "Am I wasting money?" | **Insights Widget** | `GET /insights/optimizations` |
| "What should I cancel?" | **Risk Widget** | `GET /insights/cancellation-risks` |
| "Show me this item" | **Drill-down Sheet** | `GET /{id}/transactions` |
| "This is wrong" | **Correction Flow** | `POST /ai-workflow/feedback` |
| "What's pending?" | **Pending Section** | `GET /pending` + `POST /confirm` |

---

## Page Layout

### Desktop View (2-column with sidebar)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Recurring                                    [Detect] [⚙️ Customize]   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  $1,247/mo          $14,964/yr         5 upcoming        3 ⚠️   │  │
│  │  Monthly Spend      Annual Total       This Week      Pending   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────┐  ┌───────────────────────────┐  │
│  │                                  │  │                           │  │
│  │  📺 SUBSCRIPTIONS (12)          │  │  💡 SMART INSIGHTS        │  │
│  │  ────────────────────────────── │  │  ─────────────────────────│  │
│  │  [Compact list or expandable]   │  │  • Optimization tips      │  │
│  │                                  │  │  • Cancellation risks     │  │
│  │  💡 BILLS & UTILITIES (8)       │  │  • Price hike alerts      │  │
│  │  ────────────────────────────── │  │                           │  │
│  │  [Variable amounts highlighted] │  │  ─────────────────────────│  │
│  │                                  │  │  📅 UPCOMING (14 days)   │  │
│  │  🏦 LOANS & CREDIT (4)          │  │  ─────────────────────────│  │
│  │  ────────────────────────────── │  │  Tomorrow                 │  │
│  │  [Progress bars for payoff]     │  │   Netflix $15.99          │  │
│  │                                  │  │  Dec 28                   │  │
│  │                                  │  │   Electric ~$145          │  │
│  │                                  │  │   Internet $79.99         │  │
│  └──────────────────────────────────┘  └───────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  ⚠️ NEEDS ATTENTION (3)                              [Review]   │  │
│  │  🔴 Gym membership overdue (5 days)  🟡 Spotify price +$2       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Widget System

### Why Widgets?
- Users can **rearrange** based on what matters to them
- **Collapsible** - hide what you don't need
- **Persistent** - layout saved to localStorage
- **Responsive** - stacks on mobile

### Widget Types

| Widget | Purpose | Movable | Collapsible |
|--------|---------|---------|-------------|
| **Summary Metrics** | Top-level KPIs | No (fixed top) | No |
| **Subscriptions** | Streaming, software, memberships | Yes | Yes |
| **Bills & Utilities** | Variable household expenses | Yes | Yes |
| **Loans & Credit** | Debt with payoff tracking | Yes | Yes |
| **Insights** | AI-powered recommendations | Yes | Yes |
| **Upcoming** | Calendar of due dates | Yes | Yes |
| **Attention** | Alerts and pending items | No (fixed bottom) | Yes |

### Library: `react-grid-layout`
```bash
npm install react-grid-layout
```

Features we'll use:
- `isDraggable` - User can move widgets
- `isResizable` - User can resize widgets
- `onLayoutChange` - Save to localStorage
- Breakpoints for responsive design

---

## Section Details

### 1. Summary Metrics Bar (Fixed Top)

**Endpoint:** `GET /recurring/summary`

| Metric | Data Field | Click Action |
|--------|------------|--------------|
| Monthly Spend | `total_monthly` | Show breakdown modal |
| Annual Total | `total_annual` | Show forecast |
| Upcoming | Count from `/insights/upcoming?days=7` | Scroll to Upcoming widget |
| Pending/Alerts | Count pending + overdue | Scroll to Attention section |

**Visual:** 4 cards in a row, minimal design, trend arrows if we track history

---

### 2. Category Widgets (Subscriptions / Bills / Loans)

**Endpoints:**
- `GET /recurring/subscriptions`
- `GET /recurring/bills`
- `GET /recurring/loans`

**Each widget shows:**
- Header with count and total monthly cost
- Compact list of items (top 5, "See all" expands)
- Each item: Name, Amount, Next Due, Status badge

**Item Card Design:**
```
┌─────────────────────────────────────────────┐
│ Netflix                         $15.99/mo   │
│ Streaming • Due Dec 28              ●●●●○   │
└─────────────────────────────────────────────┘
```

**Drill-down:** Click item → Slide-out sheet with:
- Full transaction history (sparkline)
- Categorization details
- Edit/Correct option
- Cancel/Archive option

---

### 3. Insights Widget

**Endpoints:**
- `GET /recurring/insights` - Natural language insights
- `GET /recurring/insights/optimizations` - Savings suggestions
- `GET /recurring/insights/cancellation-risks` - Risk analysis

**Display:**
- Prioritized list of actionable insights
- Each insight has a CTA button
- Dismissible (sends feedback to `/ai-workflow/insights/feedback`)

**Example Insights:**
```
┌─────────────────────────────────────────────┐
│ 💰 Save $104/year                           │
│ Switch 3 subscriptions to annual billing    │
│ [See Details]                      [Dismiss]│
├─────────────────────────────────────────────┤
│ ⚠️ Consider cancelling                      │
│ Planet Fitness - unused for 3 months        │
│ [View]                             [Dismiss]│
└─────────────────────────────────────────────┘
```

---

### 4. Upcoming Widget

**Endpoint:** `GET /recurring/insights/upcoming?days=14`

**Display:** Grouped by date
```
Tomorrow (Dec 25)
  └─ Netflix        $15.99

Saturday (Dec 28)
  ├─ Electric      ~$145.00
  └─ Internet       $79.99

Next Week
  └─ Car Insurance $189.00
```

**Features:**
- Toggle: All / Essential Only
- Sum for each period
- Click → Jump to item detail

---

### 5. Attention Bar (Fixed Bottom)

**Combines:**
- Overdue items (from main list where status = "overdue")
- Pending review items (`GET /recurring/pending`)
- Price hike alerts (items with `price_hike = true`)

**Design:** Horizontal scrollable cards or collapsible alert bar

**Actions:**
- Overdue → "Mark as Paid" or "Investigate"
- Pending → "Review Now" → Opens pending review flow
- Price Hike → "View History"

---

## Drill-Down Detail Sheet

When user clicks any recurring item, slide-out panel shows:

```
┌─────────────────────────────────────────────┐
│ ← Back                              [Edit]  │
├─────────────────────────────────────────────┤
│                                             │
│  Netflix                                    │
│  Streaming Video Subscription               │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ $15.99/mo        $191.88/yr           │  │
│  │ Monthly          Next: Dec 28         │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  PAYMENT HISTORY                            │
│  ─────────────────────────────────────────  │
│  [Sparkline chart showing last 12 months]   │
│                                             │
│  Dec 2024    $15.99    ✓                   │
│  Nov 2024    $15.99    ✓                   │
│  Oct 2024    $13.99    ✓  ← Price increase │
│  Sep 2024    $13.99    ✓                   │
│                                             │
│  ─────────────────────────────────────────  │
│  CLASSIFICATION                             │
│  Type: Subscription                         │
│  Category: Streaming Video                  │
│  Essential: No                              │
│  Confidence: 95%                            │
│  [This is wrong? Correct it]                │
│                                             │
│  ─────────────────────────────────────────  │
│  ACTIONS                                    │
│  [Mark as Cancelled]  [View All Txns]       │
│                                             │
└─────────────────────────────────────────────┘
```

**For Loans, additional section:**
```
  LOAN PROGRESS
  ─────────────────────────────────────────
  Lender: Ally Financial
  Remaining: ~$10,127 (18 payments)
  Payoff Date: ~June 2026

  [████████████░░░░░░░░] 62% paid
```

---

## Correction & Learning Flow

When user clicks "This is wrong? Correct it":

```
┌─────────────────────────────────────────────┐
│ Help us improve                             │
├─────────────────────────────────────────────┤
│                                             │
│ Current classification:                     │
│ Type: Bill → Utility                        │
│                                             │
│ What should it be?                          │
│ ○ Subscription                              │
│ ○ Bill (correct, but wrong category)        │
│ ○ Loan                                      │
│ ○ Not recurring (remove it)                 │
│                                             │
│ [Submit Correction]      [Cancel]           │
│                                             │
└─────────────────────────────────────────────┘
```

**Endpoint:** `POST /recurring/ai-workflow/feedback`

**Result:**
- Immediate UI update
- Toast: "Thanks! We'll learn from this."
- AI system improves for future similar items

---

## Pending Review Flow

When user clicks "Review Now" on pending items:

**Endpoint:** `GET /recurring/pending`

**UI:** Modal or dedicated section showing candidates

```
┌─────────────────────────────────────────────────────────────────┐
│ Review Detected Recurring (3 items)                    [×]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☐  Amazon Prime         $14.99/mo      Confidence: 92% │   │
│  │     Monthly • Subscription • 8 occurrences             │   │
│  │     [Confirm] [Reject] [Edit First]                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ☐  UNKNOWN MERCHANT      $49.99/mo     Confidence: 45% │   │
│  │     Monthly • Unknown • 3 occurrences                  │   │
│  │     [Confirm] [Reject] [Edit First]                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  [Confirm All High Confidence (>80%)]  [Reject All Low (<50%)] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Endpoints:**
- `POST /recurring/confirm/{id}/with-learning` - Confirm + train AI
- `POST /recurring/reject/{id}/with-learning` - Reject + train AI

---

## Implementation Tasks

### Phase 1: Foundation
- [ ] Create widget container with `react-grid-layout`
- [ ] Build Summary Metrics bar component
- [ ] Create base RecurringItemCard component
- [ ] Implement category widgets (Subscriptions, Bills, Loans)
- [ ] Add "See all" expansion for each category

### Phase 2: Insights & Upcoming
- [ ] Build Insights widget with `/insights` + `/optimizations`
- [ ] Build Upcoming widget with `/insights/upcoming`
- [ ] Add dismiss functionality with feedback API
- [ ] Implement Attention bar for alerts

### Phase 3: Drill-Down
- [ ] Create slide-out detail sheet component
- [ ] Integrate sparkline chart (`/{id}/transactions`)
- [ ] Add loan-specific progress section
- [ ] Implement correction flow UI

### Phase 4: Pending & Actions
- [ ] Build pending review modal/section
- [ ] Implement confirm/reject with learning
- [ ] Add bulk actions (confirm high confidence, etc.)
- [ ] Wire up all remaining endpoints

### Phase 5: Polish
- [ ] Persist widget layout to localStorage
- [ ] Add loading skeletons for all sections
- [ ] Mobile responsive adjustments
- [ ] Error states and empty states

---

## New Hooks Needed

```typescript
// Summary & Lists
useRecurringSummary()           // GET /recurring/summary
useSubscriptions()              // GET /recurring/subscriptions
useBills()                      // GET /recurring/bills
useLoans()                      // GET /recurring/loans

// Insights
useRecurringInsights(limit)     // GET /recurring/insights
useOptimizations(limit)         // GET /recurring/insights/optimizations
useCancellationRisks(limit)     // GET /recurring/insights/cancellation-risks
useUpcomingPayments(days)       // GET /recurring/insights/upcoming

// Detail & Actions
useRecurringTransactions(id)    // GET /recurring/{id}/transactions
useConfirmWithLearning()        // POST /recurring/confirm/{id}/with-learning
useRejectWithLearning()         // POST /recurring/reject/{id}/with-learning
useSubmitCorrection()           // POST /recurring/ai-workflow/feedback
```

---

## Endpoint Coverage

| Endpoint | Used In | Status |
|----------|---------|--------|
| `GET /recurring/summary` | Summary Metrics | 🔲 TODO |
| `GET /recurring/subscriptions` | Subscriptions Widget | 🔲 TODO |
| `GET /recurring/bills` | Bills Widget | 🔲 TODO |
| `GET /recurring/loans` | Loans Widget | 🔲 TODO |
| `GET /recurring/pending` | Pending Review | ✅ EXISTS |
| `GET /recurring/insights` | Insights Widget | 🔲 TODO |
| `GET /recurring/insights/optimizations` | Insights Widget | 🔲 TODO |
| `GET /recurring/insights/cancellation-risks` | Insights Widget | 🔲 TODO |
| `GET /recurring/insights/upcoming` | Upcoming Widget | 🔲 TODO |
| `GET /recurring/{id}/transactions` | Detail Sheet | ✅ EXISTS (unused) |
| `POST /recurring/confirm/{id}/with-learning` | Review Flow | 🔲 TODO |
| `POST /recurring/reject/{id}/with-learning` | Review Flow | 🔲 TODO |
| `POST /recurring/ai-workflow/feedback` | Correction Flow | 🔲 TODO |
| `POST /recurring/suggest` | Detect Button | ✅ EXISTS |

**Coverage after implementation: 14 key endpoints used (vs 5 currently)**

---

## Success Criteria

1. **User can see total recurring spend in <2 seconds** (hero metrics)
2. **Categories are clearly separated** (subscriptions vs bills vs loans)
3. **Actionable insights are visible** (not hidden in menus)
4. **Drill-down is one click away** (detail sheet)
5. **Corrections are easy** (inline feedback)
6. **Layout is customizable** (movable widgets)
7. **Mobile works** (responsive stacking)

---

## Notes

- Keep existing functionality working during migration
- Use shadcn/ui components for consistency with rest of app
- Progressive enhancement: basic view works, widgets are optional
- Consider: should we show cash flow forecast chart? (Maybe Phase 2)
