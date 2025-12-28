# KASHAT UI RESTRUCTURE - COMPLETE IMPLEMENTATION GUIDE
## For Claude Code CLI

---

## MISSION

Transform Kashat from a cluttered 15-page app with hidden features into a clean, intuitive 11-page app where Net Worth is a first-class citizen and every page has one clear purpose.

**Key Deliverables:**
1. NEW Net Worth page with full asset/liability tracking
2. Redesigned Dashboard (no tabs, always-visible metrics)
3. Delete 4 redundant pages
4. Rename 2 pages for clarity
5. Fix all broken features
6. Update documentation throughout

**Location:** `C:\Users\Marwan\Desktop\AI\Flos`

**CRITICAL RULE:** After completing each phase, update the relevant documentation files. Never leave docs stale.

---

## REFERENCE DOCUMENTS

Read these before starting:
- `docs/KASHAT_PAGE_INVENTORY.md` - Current page structure
- `docs/KASHAT_COMPONENT_INVENTORY.md` - All components
- `docs/KASHAT_UI_ISSUES.md` - Known problems
- `docs/KASHAT_UI_RESTRUCTURE_PROPOSAL.md` - Original proposal
- `docs/KASHAT_FUTURE_FEATURES.md` - Feature roadmap

---

## PHASE 1: NET WORTH BACKEND
**Goal:** Create database tables and API endpoints for assets/liabilities

### 1.1 Database Schema

Create migration or add to `db.py`:

```sql
-- Manual Assets Table
CREATE TABLE IF NOT EXISTS asset (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,  -- real_estate, vehicle, precious_metal, investment, business, other
    subtype TEXT,              -- house, car, gold, 401k, etc.
    
    -- Value tracking
    current_value REAL NOT NULL DEFAULT 0,
    purchase_price REAL,
    purchase_date TEXT,
    
    -- For precious metals
    weight_oz REAL,
    weight_unit TEXT DEFAULT 'oz',  -- oz, grams
    spot_price REAL,
    premium_paid REAL,
    metal_type TEXT,  -- gold, silver, platinum, palladium
    
    -- For real estate
    address TEXT,
    property_type TEXT,  -- single_family, condo, land, commercial
    
    -- For vehicles
    year INTEGER,
    make TEXT,
    model TEXT,
    vin TEXT,
    
    -- For investments
    institution TEXT,
    account_type TEXT,  -- 401k, ira, brokerage, hsa, crypto
    
    -- For business
    valuation_method TEXT,
    monthly_revenue REAL,
    multiplier REAL,
    
    -- Metadata
    notes TEXT,
    is_liquid BOOLEAN DEFAULT FALSE,
    
    -- Auto-update settings
    auto_update BOOLEAN DEFAULT FALSE,
    update_source TEXT,  -- manual, zillow, kbb, spot_price
    last_updated TEXT,
    update_reminder TEXT,  -- monthly, quarterly, never
    
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Liabilities Table
CREATE TABLE IF NOT EXISTS liability (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    liability_type TEXT NOT NULL,  -- mortgage, auto_loan, personal_loan, student_loan, credit_card, other
    
    -- Loan details
    original_amount REAL,
    current_balance REAL NOT NULL DEFAULT 0,
    interest_rate REAL,
    monthly_payment REAL,
    
    -- Linked asset (for mortgages/auto loans)
    linked_asset_id TEXT,
    
    -- Dates
    start_date TEXT,
    expected_payoff_date TEXT,
    
    -- Metadata
    lender TEXT,
    account_number TEXT,
    notes TEXT,
    
    -- Auto-tracking
    auto_calculate BOOLEAN DEFAULT FALSE,  -- For credit cards, calculate from transactions
    linked_account_id TEXT,  -- Link to bank account for auto-tracking
    
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    
    FOREIGN KEY (linked_asset_id) REFERENCES asset(id) ON DELETE SET NULL
);

-- Net Worth Snapshots (for history)
-- Already exists, but ensure it captures manual assets too
CREATE INDEX IF NOT EXISTS idx_asset_type ON asset(asset_type);
CREATE INDEX IF NOT EXISTS idx_liability_type ON liability(liability_type);
```

### 1.2 Backend API Routes

Create `apps/backend/src/kashat/api/routes/assets.py`:

```python
"""
Assets & Liabilities API - Full net worth tracking

Endpoints:
- GET /api/assets - List all assets
- POST /api/assets - Create asset
- GET /api/assets/{id} - Get single asset
- PUT /api/assets/{id} - Update asset
- DELETE /api/assets/{id} - Delete asset
- POST /api/assets/{id}/update-value - Update current value
- GET /api/assets/summary - Asset breakdown by type

- GET /api/liabilities - List all liabilities
- POST /api/liabilities - Create liability
- PUT /api/liabilities/{id} - Update liability
- DELETE /api/liabilities/{id} - Delete liability

- GET /api/networth/complete - Full net worth with assets + liabilities
- POST /api/networth/snapshot - Create snapshot including manual assets
- GET /api/metals/spot - Get live precious metal prices
"""

# Implement all endpoints with full CRUD
# Include live metal price fetching from free API
```

### 1.3 Precious Metals Live Pricing

```python
# In assets.py or separate metals.py

import httpx

METAL_APIS = {
    "gold": "https://api.metals.live/v1/spot/gold",
    "silver": "https://api.metals.live/v1/spot/silver",
    "platinum": "https://api.metals.live/v1/spot/platinum",
    "palladium": "https://api.metals.live/v1/spot/palladium",
}

async def get_spot_price(metal: str) -> float:
    """Fetch current spot price for a metal."""
    url = METAL_APIS.get(metal.lower())
    if not url:
        raise ValueError(f"Unknown metal: {metal}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        return float(data[0]["price"])  # Adjust based on actual API response

async def update_all_metal_assets():
    """Update all precious metal assets with current spot prices."""
    conn = get_conn()
    metals = conn.execute(
        "SELECT id, metal_type, weight_oz FROM asset WHERE asset_type = 'precious_metal'"
    ).fetchall()
    
    for asset_id, metal_type, weight in metals:
        try:
            spot = await get_spot_price(metal_type)
            value = spot * weight
            conn.execute(
                "UPDATE asset SET spot_price = ?, current_value = ?, last_updated = ? WHERE id = ?",
                [spot, value, datetime.now().isoformat(), asset_id]
            )
        except Exception as e:
            logger.error(f"Failed to update metal {asset_id}: {e}")
    
    conn.commit()
```

### 1.4 Register Routes

In `apps/backend/src/kashat/api/__init__.py`, add:

```python
from .routes.assets import router as assets_router

# In create_app():
app.include_router(assets_router, prefix="/api")
```

### 1.5 Update Net Worth Endpoint

Modify `routes/networth.py` to include manual assets:

```python
@router.get("/complete")
def get_complete_net_worth() -> CompleteNetWorthResponse:
    """Get net worth including all manual assets and liabilities."""
    conn = get_conn()
    
    # Bank accounts (existing logic)
    bank_total = calculate_bank_balances(conn)
    
    # Manual assets
    assets = conn.execute("SELECT * FROM asset").fetchall()
    assets_total = sum(a["current_value"] for a in assets)
    
    # Liabilities
    liabilities = conn.execute("SELECT * FROM liability").fetchall()
    liabilities_total = sum(l["current_balance"] for l in liabilities)
    
    # Breakdown by type
    asset_breakdown = {}
    for asset in assets:
        t = asset["asset_type"]
        asset_breakdown[t] = asset_breakdown.get(t, 0) + asset["current_value"]
    
    return CompleteNetWorthResponse(
        total_assets=bank_total + assets_total,
        bank_accounts=bank_total,
        manual_assets=assets_total,
        total_liabilities=liabilities_total,
        net_worth=(bank_total + assets_total) - liabilities_total,
        asset_breakdown=asset_breakdown,
        assets=[AssetResponse(**dict(a)) for a in assets],
        liabilities=[LiabilityResponse(**dict(l)) for l in liabilities],
        as_of=datetime.now().isoformat()
    )
```

### 1.6 Documentation Update

After completing Phase 1, update:
- `docs/KASHAT_FUTURE_FEATURES.md` - Mark "Manual Assets" as IMPLEMENTED
- `docs/KASHAT_PAGE_INVENTORY.md` - Add new /networth page entry (placeholder)

---

## PHASE 2: NET WORTH FRONTEND
**Goal:** Create the Net Worth page with asset/liability management

### 2.1 Create Net Worth Page

Create `apps/web/src/app/networth/page.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { 
  Plus, Home, Car, Coins, TrendingUp, Briefcase, Package,
  CreditCard, Building, Edit2, Trash2, RefreshCw
} from 'lucide-react'
import { client } from '@/lib/api-client'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { AddAssetDialog } from '@/components/networth/AddAssetDialog'
import { AddLiabilityDialog } from '@/components/networth/AddLiabilityDialog'
import { NetWorthChart } from '@/components/networth/NetWorthChart'

// Full implementation with:
// - Summary cards (total net worth, assets, liabilities)
// - Asset list grouped by type with edit/delete
// - Liability list with linked assets shown
// - Net worth over time chart
// - Add Asset button → opens modal
// - Add Liability button → opens modal
// - Refresh metal prices button
```

### 2.2 Create Asset Dialog Component

Create `apps/web/src/components/networth/AddAssetDialog.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

// Asset type selection (tabs or buttons):
// 🏠 Real Estate | 🚗 Vehicle | 🥇 Precious Metals | 📈 Investment | 🏪 Business | 📦 Other

// Dynamic form based on asset type:
// - Real Estate: name, address, property_type, purchase_price, current_value, purchase_date
// - Vehicle: name, year, make, model, purchase_price, current_value
// - Precious Metals: metal_type, form, weight_oz, purchase_price (shows live spot price)
// - Investment: name, institution, account_type, current_balance
// - Business: name, valuation_method, inventory_value, monthly_revenue, multiplier
// - Other: name, description, current_value

// Include:
// - Live spot price display for precious metals
// - Auto-update toggle for metals
// - Link liability option for real estate/vehicles
```

### 2.3 Create Liability Dialog Component

Create `apps/web/src/components/networth/AddLiabilityDialog.tsx`:

```tsx
// Liability types:
// 🏠 Mortgage | 🚗 Auto Loan | 🎓 Student Loan | 💳 Credit Card | 📋 Personal Loan | 📦 Other

// Fields:
// - name, liability_type, original_amount, current_balance
// - interest_rate, monthly_payment
// - lender, start_date, expected_payoff_date
// - linked_asset_id (dropdown of assets)
// - For credit cards: option to auto-calculate from transactions
```

### 2.4 Create Hooks

Create `apps/web/src/hooks/useAssets.ts`:

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

export function useAssets() {
  return useQuery({
    queryKey: ['assets'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/assets')
      if (error) throw error
      return data
    }
  })
}

export function useCreateAsset() { /* ... */ }
export function useUpdateAsset() { /* ... */ }
export function useDeleteAsset() { /* ... */ }

export function useLiabilities() { /* ... */ }
export function useCreateLiability() { /* ... */ }
export function useUpdateLiability() { /* ... */ }
export function useDeleteLiability() { /* ... */ }

export function useCompleteNetWorth() {
  return useQuery({
    queryKey: ['networth', 'complete'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/networth/complete')
      if (error) throw error
      return data
    }
  })
}

export function useMetalSpotPrices() { /* ... */ }
export function useRefreshMetalPrices() { /* ... */ }
```

### 2.5 Create Net Worth Chart Component

Create `apps/web/src/components/networth/NetWorthChart.tsx`:

```tsx
// Line chart showing net worth over time
// Use existing Recharts setup
// Show: Total, Assets, Liabilities as separate lines
// Annotations for major changes
```

### 2.6 Asset Type Icons Map

```tsx
const ASSET_ICONS = {
  real_estate: Home,
  vehicle: Car,
  precious_metal: Coins,
  investment: TrendingUp,
  business: Briefcase,
  other: Package,
}

const LIABILITY_ICONS = {
  mortgage: Building,
  auto_loan: Car,
  student_loan: GraduationCap,
  credit_card: CreditCard,
  personal_loan: FileText,
  other: Package,
}
```

### 2.7 Documentation Update

Update `docs/KASHAT_PAGE_INVENTORY.md`:
- Add full entry for /networth page with all components, APIs, features

---

## PHASE 3: DASHBOARD REDESIGN
**Goal:** Remove tabs, add always-visible metrics, merge Analytics content

### 3.1 Create Dashboard Header Component

Create `apps/web/src/components/dashboard/DashboardHeader.tsx`:

```tsx
'use client'

import { useCompleteNetWorth } from '@/hooks/useAssets'
import { useAnalyticsSummary } from '@/hooks/useAnalytics'
import { useBudgets } from '@/hooks/useBudgets'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { TrendingUp, TrendingDown } from 'lucide-react'
import Link from 'next/link'

export function DashboardHeader() {
  const { data: netWorth } = useCompleteNetWorth()
  const { data: summary } = useAnalyticsSummary()
  const { data: budgets } = useBudgets()
  
  // Calculate budget usage
  const activeBudget = budgets?.[0]
  const budgetPercent = activeBudget ? /* calculate */ 72 : null
  
  return (
    <div className="grid grid-cols-3 gap-4 p-4 bg-card rounded-lg border mb-6">
      {/* Net Worth - Clickable */}
      <Link href="/networth" className="hover:bg-accent rounded-lg p-3 transition-colors">
        <div className="text-sm text-muted-foreground">Net Worth</div>
        <div className="text-2xl font-bold">
          <AnimatedCurrency value={netWorth?.net_worth ?? 0} />
        </div>
        <div className="text-xs text-green-600 flex items-center gap-1">
          <TrendingUp className="h-3 w-3" />
          +2.3% this month
        </div>
      </Link>
      
      {/* This Month Cash Flow */}
      <div className="p-3">
        <div className="text-sm text-muted-foreground">This Month</div>
        <div className="text-2xl font-bold">
          <AnimatedCurrency value={summary?.cashflow ?? 0} />
        </div>
        <div className="text-xs text-muted-foreground">
          vs {summary?.prev_cashflow ?? 0} last month
        </div>
      </div>
      
      {/* Budget Status */}
      <Link href="/budget" className="hover:bg-accent rounded-lg p-3 transition-colors">
        <div className="text-sm text-muted-foreground">Budget</div>
        <div className="text-2xl font-bold">{budgetPercent ?? '--'}% used</div>
        <div className="text-xs text-muted-foreground">
          ${activeBudget?.remaining ?? '--'} left
        </div>
      </Link>
    </div>
  )
}
```

### 3.2 Redesign Dashboard Page

Modify `apps/web/src/app/page.tsx`:

```tsx
'use client'

// REMOVE all tab logic
// KEEP all the hooks and data fetching

import { DashboardHeader } from '@/components/dashboard/DashboardHeader'

export default function DashboardPage() {
  // ... existing hooks ...
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Always-visible header with key metrics */}
      <DashboardHeader />
      
      {/* Section 1: Financial Health */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Financial Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <HealthScoreCard />
          <RunwayCard />
          <SavingsRateCard /> {/* New or extracted from CashflowSummaryCard */}
        </div>
      </section>
      
      {/* Section 2: Spending Overview */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Spending Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SpendingChart data={monthlyData} /> {/* Income vs Spending line chart */}
          <CategoryBreakdown data={categoryData} /> {/* Pie chart */}
        </div>
      </section>
      
      {/* Section 3: Upcoming & Action Items */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Upcoming & Insights</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <UpcomingBillsCard />
          <AIInsightsWidget />
        </div>
      </section>
      
      {/* Section 4: Recent Activity */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <RecentTransactionsCard limit={10} />
      </section>
    </div>
  )
}
```

### 3.3 Create Recent Transactions Card

Create `apps/web/src/components/dashboard/RecentTransactionsCard.tsx`:

```tsx
// Shows last N transactions in a compact table
// Links to /transactions for full view
// Quick category assignment dropdown
```

### 3.4 Remove Tab Components

Delete or comment out:
- Tab navigation from dashboard
- Separate Spending/Trends/Forecast tab content (integrate into main page or remove)

### 3.5 Documentation Update

Update `docs/KASHAT_PAGE_INVENTORY.md`:
- Update Dashboard entry to reflect new structure
- Remove references to tabs
- Document new DashboardHeader component

---

## PHASE 4: CLEANUP REDUNDANT PAGES
**Goal:** Delete duplicate pages, update navigation

### 4.1 Delete Redundant Pages

```bash
# Delete these files:
rm apps/web/src/app/analytics/page.tsx
rm -rf apps/web/src/app/analytics/

rm apps/web/src/app/categories/page.tsx
rm -rf apps/web/src/app/categories/

rm apps/web/src/app/rules/page.tsx
rm -rf apps/web/src/app/rules/

rm apps/web/src/app/pulse/page.tsx
rm -rf apps/web/src/app/pulse/
```

### 4.2 Add Redirects

In `apps/web/next.config.js`, update redirects:

```js
async redirects() {
  return [
    // Existing redirects...
    
    // New redirects for removed pages
    { source: '/analytics', destination: '/', permanent: true },
    { source: '/categories', destination: '/settings/categories', permanent: true },
    { source: '/rules', destination: '/settings/automation', permanent: true },
    { source: '/pulse', destination: '/settings/system', permanent: true },
  ]
}
```

### 4.3 Update Sidebar Navigation

Modify `apps/web/src/components/layout/Sidebar.tsx`:

```tsx
const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/" },
  { icon: Wallet, label: "Net Worth", href: "/networth" },        // NEW
  { icon: ArrowLeftRight, label: "Transactions", href: "/transactions" },
  { icon: Receipt, label: "Bills", href: "/bills" },               // RENAMED
  { icon: Repeat, label: "Subscriptions", href: "/subscriptions" }, // RENAMED
  { icon: Users, label: "Transfers", href: "/transfers" },
  { icon: Settings, label: "Settings", href: "/settings" },
]

// REMOVED: Analytics, Calendar (renamed), Recurring (renamed), Budget (moved to dashboard), Import (moved to header)
```

### 4.4 Add Import Button to Header/Layout

In layout or header component, add quick import action:

```tsx
// Option A: Add to header
<Button variant="outline" size="sm" asChild>
  <Link href="/import">
    <Upload className="h-4 w-4 mr-2" />
    Import
  </Link>
</Button>

// Option B: Floating Action Button (mobile-friendly)
// Add FAB component in bottom-right corner
```

### 4.5 Documentation Update

Update `docs/KASHAT_PAGE_INVENTORY.md`:
- Remove entries for deleted pages
- Add note about redirects
- Update sidebar item count

Update `docs/KASHAT_UI_ISSUES.md`:
- Mark redundancy issues as RESOLVED

---

## PHASE 5: RENAME PAGES
**Goal:** Rename Calendar → Bills, Recurring → Subscriptions

### 5.1 Rename Calendar to Bills

```bash
# Rename directory
mv apps/web/src/app/calendar apps/web/src/app/bills
```

Update the page file:
- Change page title to "Bills"
- Update any internal references

### 5.2 Rename Recurring to Subscriptions

```bash
# Rename directory
mv apps/web/src/app/recurring apps/web/src/app/subscriptions
```

Update the page file:
- Change page title to "Subscriptions"
- Update any internal references

### 5.3 Update All References

Search and replace across codebase:
- `/calendar` → `/bills`
- `/recurring` → `/subscriptions`
- `"Calendar"` → `"Bills"`
- `"Recurring"` → `"Subscriptions"`

Files to check:
- All page files
- Sidebar.tsx
- Any navigation components
- Dashboard links
- next.config.js redirects

### 5.4 Add Redirects for Old Routes

```js
// next.config.js
{ source: '/calendar', destination: '/bills', permanent: true },
{ source: '/recurring', destination: '/subscriptions', permanent: true },
```

### 5.5 Documentation Update

Update all docs:
- `KASHAT_PAGE_INVENTORY.md` - Rename entries
- `KASHAT_COMPONENT_INVENTORY.md` - Update component locations
- `KASHAT_UI_RESTRUCTURE_PROPOSAL.md` - Mark renames as COMPLETE

---

## PHASE 6: FIX BROKEN FEATURES
**Goal:** Fix budget progress, overdue bills, transfer filters

### 6.1 Fix Budget Progress Endpoint

In `apps/backend/src/kashat/api/routes/budgets.py`:

```python
@router.get("/{budget_id}/progress")
def get_budget_progress(budget_id: str) -> BudgetProgress:
    """Calculate spending progress against budget limits."""
    conn = get_conn()
    
    # Get budget
    budget = conn.execute(
        "SELECT * FROM budget WHERE id = ?", [budget_id]
    ).fetchone()
    
    if not budget:
        raise HTTPException(404, "Budget not found")
    
    # Get category limits
    limits = conn.execute(
        "SELECT * FROM budget_category WHERE budget_id = ?", [budget_id]
    ).fetchall()
    
    # Calculate period dates based on budget.period
    period_start, period_end = get_current_period(budget["period"])
    
    # Calculate spending per category
    categories = []
    total_limit = 0
    total_spent = 0
    
    for limit in limits:
        spent = conn.execute("""
            SELECT COALESCE(SUM(ABS(t.amount)), 0) as spent
            FROM [transaction] t
            JOIN transaction_category tc ON t.id = tc.tx_id
            WHERE tc.category_id = ?
            AND t.posted_at BETWEEN ? AND ?
            AND t.amount < 0
        """, [limit["category_id"], period_start, period_end]).fetchone()["spent"]
        
        categories.append({
            "category_id": limit["category_id"],
            "limit": limit["amount_limit"],
            "spent": spent,
            "remaining": limit["amount_limit"] - spent,
            "percent": (spent / limit["amount_limit"] * 100) if limit["amount_limit"] > 0 else 0
        })
        
        total_limit += limit["amount_limit"]
        total_spent += spent
    
    return BudgetProgress(
        budget_id=budget_id,
        period_start=period_start,
        period_end=period_end,
        total_limit=total_limit,
        total_spent=total_spent,
        total_remaining=total_limit - total_spent,
        percent_used=(total_spent / total_limit * 100) if total_limit > 0 else 0,
        categories=categories
    )
```

### 6.2 Fix Overdue Bills (Remove Section or Implement)

**Option A: Remove overdue section from Bills page**

In `apps/web/src/app/bills/page.tsx`, remove or hide the Overdue section.

**Option B: Implement proper tracking**

This requires adding `next_date` to recurring_series and updating it when payments are detected. More complex - recommend Option A for now.

### 6.3 Fix Transfer Service Filter

In `apps/backend/src/kashat/api/routes/p2p.py`:

```python
@router.get("/counterparties")
def get_counterparties(
    service: Optional[str] = Query(None, description="Filter by service: zelle, venmo, cashapp, etc.")
) -> List[Counterparty]:
    conn = get_conn()
    
    query = "SELECT * FROM counterparty"
    params = []
    
    if service:
        # Join with p2p_transaction to filter by service
        query = """
            SELECT DISTINCT c.* FROM counterparty c
            JOIN p2p_transaction p ON c.name_normalized = p.counterparty_normalized
            WHERE p.service = ?
        """
        params = [service.lower()]
    
    rows = conn.execute(query, params).fetchall()
    return [Counterparty(**dict(r)) for r in rows]
```

Update frontend to pass service parameter.

### 6.4 Remove Link Recurring Stub

In transfers page, either:
- Implement the feature properly
- OR remove the button entirely

For now, remove the button:

```tsx
// Remove or comment out:
// <Button onClick={() => console.log('Link Recurring', id)}>Link Recurring</Button>
```

### 6.5 Documentation Update

Update `docs/KASHAT_UI_ISSUES.md`:
- Mark fixed issues as RESOLVED
- Note any deferred items

---

## PHASE 7: FINAL POLISH
**Goal:** Standardize UI, add error boundaries, cleanup

### 7.1 Add Error Boundaries to Dashboard Cards

Create `apps/web/src/components/ui/CardErrorBoundary.tsx`:

```tsx
'use client'

import { Component, ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'

export class CardErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean }
> {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Card className="bg-destructive/10 border-destructive/20">
          <CardContent className="flex items-center gap-2 p-4 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">Failed to load</span>
          </CardContent>
        </Card>
      )
    }
    return this.props.children
  }
}
```

Wrap all dashboard cards:

```tsx
<CardErrorBoundary>
  <NetWorthCard />
</CardErrorBoundary>
```

### 7.2 Standardize Loading States

Ensure all cards use `CardSkeleton` from `LoadingSpinner.tsx`:

```tsx
if (isLoading) return <CardSkeleton className="h-40" />
```

### 7.3 Remove Dead Code

After verifying unused, delete:
- `apps/web/src/components/charts/CategoryPieChart.tsx` (if only used on deleted Analytics)
- `apps/web/src/components/charts/MonthlyBarChart.tsx` (if only used on deleted Analytics)
- Any other components identified in inventory as unused

### 7.4 Verify Mobile Navigation

Test that `BottomNav.tsx` and `MobileNav.tsx` are working. If not used, remove.

### 7.5 Final Documentation Update

Update all documentation files to reflect final state:
- `KASHAT_PAGE_INVENTORY.md` - Final page list
- `KASHAT_COMPONENT_INVENTORY.md` - Final component list
- `KASHAT_UI_ISSUES.md` - All issues resolved or documented
- `KASHAT_UI_RESTRUCTURE_PROPOSAL.md` - Mark as COMPLETE

Create new summary doc `docs/KASHAT_UI_FINAL_STATE.md`:

```markdown
# KASHAT UI - FINAL STATE

## Summary
- **Total Pages:** 11 (was 15)
- **Sidebar Items:** 7 (was 9)
- **Redundant Pages:** 0 (was 4)
- **Broken Features:** 0 (was 4)

## Page Structure
1. Dashboard (/) - Command center with always-visible metrics
2. Net Worth (/networth) - Full asset/liability tracking
3. Transactions (/transactions) - Browse and categorize
4. Bills (/bills) - Upcoming payment calendar
5. Subscriptions (/subscriptions) - Recurring payments
6. Transfers (/transfers) - P2P tracking
7. Import (/import) - Statement upload
8. Settings (/settings) - All configuration
   - /settings/categories
   - /settings/automation
   - /settings/ai
   - /settings/system

## Key Features
- Net Worth tracks: Bank accounts, real estate, vehicles, precious metals (live prices), investments, business value
- Dashboard shows key metrics without clicking tabs
- AI insights prominent on dashboard
- Single path to each feature (no duplicates)

## Completed: [DATE]
```

---

## EXECUTION CHECKLIST

```
PHASE 1: Net Worth Backend
[ ] Create asset table schema
[ ] Create liability table schema
[ ] Implement /api/assets endpoints (CRUD)
[ ] Implement /api/liabilities endpoints (CRUD)
[ ] Implement /api/networth/complete endpoint
[ ] Implement /api/metals/spot endpoint
[ ] Register routes in __init__.py
[ ] Test all endpoints
[ ] Update documentation

PHASE 2: Net Worth Frontend
[ ] Create /networth page
[ ] Create AddAssetDialog component
[ ] Create AddLiabilityDialog component
[ ] Create useAssets hooks
[ ] Create NetWorthChart component
[ ] Test full CRUD flow
[ ] Test live metal prices
[ ] Update documentation

PHASE 3: Dashboard Redesign
[ ] Create DashboardHeader component
[ ] Remove tabs from dashboard
[ ] Create scrollable sections
[ ] Create RecentTransactionsCard
[ ] Merge relevant Analytics content
[ ] Test all sections load correctly
[ ] Update documentation

PHASE 4: Cleanup Redundant Pages
[ ] Delete /analytics
[ ] Delete /categories
[ ] Delete /rules
[ ] Delete /pulse
[ ] Add redirects in next.config.js
[ ] Update Sidebar navigation
[ ] Add Import button to header
[ ] Update documentation

PHASE 5: Rename Pages
[ ] Rename /calendar → /bills
[ ] Rename /recurring → /subscriptions
[ ] Update all references
[ ] Add redirects
[ ] Update Sidebar
[ ] Update documentation

PHASE 6: Fix Broken Features
[ ] Implement budget progress endpoint
[ ] Fix or remove overdue bills section
[ ] Wire up transfer service filter
[ ] Remove Link Recurring stub
[ ] Test all fixes
[ ] Update documentation

PHASE 7: Final Polish
[ ] Add error boundaries to all cards
[ ] Standardize loading states
[ ] Remove dead code
[ ] Verify mobile navigation
[ ] Final documentation update
[ ] Create KASHAT_UI_FINAL_STATE.md

FINAL VERIFICATION
[ ] All 7 sidebar links work
[ ] No 404 errors
[ ] Net worth shows all asset types
[ ] Dashboard loads without tabs
[ ] All redirects work
[ ] No console errors
[ ] Mobile navigation works
[ ] All docs up to date
```

---

## SUCCESS CRITERIA

After completing all phases:

1. **Net Worth is complete** - Shows bank accounts + manual assets + liabilities
2. **Dashboard is clean** - No tabs, key metrics always visible
3. **No redundant pages** - 11 pages total, each with unique purpose
4. **All features work** - Budget progress, filters, all buttons functional
5. **Documentation is current** - All 4 report files updated
6. **Navigation is intuitive** - 7 sidebar items, clear hierarchy

---

*Execute phase by phase. Update documentation after each phase. Test thoroughly before moving to next phase.*
