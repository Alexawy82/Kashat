# KASHAT FUTURE FEATURES ROADMAP
## Practical Features to Complete the Financial Picture

---

## OVERVIEW

These are **practical completeness** features, not moonshots. Without them, Kashat is missing key functionality for real financial management.

| Feature | Priority | Effort | Impact | Status |
|---------|----------|--------|--------|--------|
| Comprehensive Reports | HIGH | 1-2 weeks | 🔥🔥🔥 | Pending |
| Tax Support | HIGH | 1-2 weeks | 🔥🔥🔥 | Pending |
| Multi-Year/Account UI | HIGH | 3-5 days | 🔥🔥🔥 | Pending |
| Manual Assets (Net Worth) | HIGH | 1 week | 🔥🔥🔥 | ✅ IMPLEMENTED |
| AI Chat (OpenAI) | HIGH | 1 week | 🔥🔥🔥 | Pending |

**Total Estimated Effort: 5-7 weeks**

---

## FEATURE 1: COMPREHENSIVE REPORTS

### What It Does
Generate detailed, AI-powered reports covering ALL data points.

### Data Points Included

```
REPORT CONTENTS:
├── Transaction Overview
│   ├── Total count, date range
│   ├── Credits vs Debits
│   └── Net cash flow
│
├── P2P Activity (ALL 6 platforms)
│   ├── Zelle, Venmo, CashApp, PayPal, Western Union, Wire
│   ├── Sent vs Received per platform
│   ├── Top recipients & senders
│   └── AI insight on P2P patterns
│
├── Recurring Payments (81 series)
│   ├── Subscriptions (count, total, unused)
│   ├── Bills (housing, utilities, insurance, loans)
│   ├── Income sources
│   ├── Price changes detected
│   └── AI recommendations (cancel unused)
│
├── Transfers
│   ├── Internal transfer count & volume
│   ├── Account flow patterns
│   └── Credit card payment tracking
│
├── Spending by Category
│   ├── All categories with amounts & percentages
│   ├── Month-over-month trends
│   └── Year-over-year comparison
│
├── Top Merchants
│   ├── Ranked by spend
│   ├── Transaction frequency
│   └── Category breakdown per merchant
│
├── Patterns Detected
│   ├── Weekly patterns (weekend vs weekday)
│   ├── Monthly patterns (bill timing)
│   ├── Seasonal patterns
│   └── Behavioral insights
│
├── Anomalies
│   ├── Unusual transactions flagged
│   ├── Potential fraud alerts
│   └── Verification status
│
├── Business vs Personal (if applicable)
│   ├── Business expenses breakdown
│   ├── Revenue tracking
│   ├── Profit margin
│   └── Tax deduction value
│
├── Goals & Projections
│   ├── Progress on savings goals
│   ├── Projected completion dates
│   └── Net worth trend
│
└── AI Executive Summary
    ├── Key wins
    ├── Key concerns
    ├── Top 3 recommendations
    └── Projected outcomes
```

### Report Types

| Report | Frequency | Use Case |
|--------|-----------|----------|
| Monthly Summary | Monthly | Regular check-in |
| Year-End Report | Annual | Tax prep, planning |
| Business Report | Monthly/Quarterly | Mr. Patches tracking |
| Tax Prep Report | Annual | Deduction summary |
| Net Worth Report | Monthly | Wealth tracking |
| Custom Report | On-demand | Specific analysis |

### Output Formats
- [ ] PDF (beautiful, printable)
- [ ] Markdown (readable, shareable)
- [ ] JSON (data export)
- [ ] CSV (spreadsheet compatible)

### AI Integration
- **Insights Generator**: Writes executive summary
- **Pattern Analyzer**: Identifies trends
- **Financial Advisor**: Provides recommendations
- **Anomaly Detector**: Flags concerns

---

## FEATURE 2: TAX SUPPORT

### What It Does
Track deductible expenses, split business/personal, generate tax-ready reports.

### Features

```
TAX SUPPORT:
├── Transaction Tagging
│   ├── Mark as "tax deductible"
│   ├── Mark as "business expense"
│   ├── Mark as "personal"
│   └── Bulk tagging tools
│
├── Auto-Detection (AI-powered)
│   ├── Medical expenses
│   ├── Charitable donations
│   ├── Business expenses
│   ├── State/local taxes paid
│   └── Potential deductions missed
│
├── Business/Personal Split
│   ├── Clear separation of transactions
│   ├── Mixed-use expense allocation
│   │   ├── Home office percentage
│   │   ├── Internet (% business)
│   │   ├── Phone (% business)
│   │   └── Vehicle (if applicable)
│   └── Running totals
│
├── Tax Reports
│   ├── Schedule C Helper (Business Income)
│   │   ├── Revenue summary
│   │   ├── Expenses by category
│   │   ├── Net profit/loss
│   │   └── Quarterly breakdown
│   │
│   ├── Itemized Deductions Summary
│   │   ├── Medical (with AGI floor calc)
│   │   ├── Charitable
│   │   ├── State/local taxes
│   │   └── Other deductions
│   │
│   └── Standard vs Itemized Comparison
│       └── "Itemizing saves you $X" or "Take standard"
│
├── Deduction Finder (AI)
│   ├── Scan for missed deductions
│   ├── Suggest categories to review
│   └── Estimate tax savings
│
└── Export
    ├── CSV for CPA
    ├── TurboTax compatible format
    └── Categorized expense list
```

### Database Changes

```sql
-- Add tax fields to transactions
ALTER TABLE transactions ADD COLUMN is_tax_deductible BOOLEAN DEFAULT FALSE;
ALTER TABLE transactions ADD COLUMN is_business_expense BOOLEAN DEFAULT FALSE;
ALTER TABLE transactions ADD COLUMN tax_category TEXT; -- medical, charitable, business, etc.

-- Tax deduction tracking table
CREATE TABLE tax_deductions (
    id TEXT PRIMARY KEY,
    year INTEGER,
    category TEXT, -- schedule_c, schedule_a, etc.
    subcategory TEXT, -- medical, charitable, home_office, etc.
    amount REAL,
    transaction_ids JSON, -- linked transactions
    notes TEXT,
    created_at TEXT
);

-- Business expense tracking
CREATE TABLE business_expenses (
    id TEXT PRIMARY KEY,
    business_name TEXT, -- "Mr. Patches"
    year INTEGER,
    category TEXT, -- inventory, shipping, advertising, etc.
    amount REAL,
    transaction_ids JSON,
    created_at TEXT
);
```

### AI Integration
- **Categorizer**: Auto-detect deductible transactions
- **Pattern Analyzer**: Find recurring deductible expenses
- **Financial Advisor**: Recommend itemize vs standard
- **Insights Generator**: Summarize tax situation

---

## FEATURE 3: MULTI-YEAR / MULTI-ACCOUNT UI

### What It Does
Proper UI for managing multiple accounts and viewing multi-year data.

### Current State
```
✅ Backend supports multi-account
✅ Backend supports multi-year data
✅ Transfer detection works cross-account
⚠️ UI needs work
```

### UI Additions

```
MULTI-ACCOUNT UI:
├── Account Management Page
│   ├── List all accounts
│   ├── Add new account
│   ├── Edit account (name, type, institution)
│   ├── Delete account (with transaction handling)
│   ├── Set account as primary
│   └── Account balance history chart
│
├── Account Selector (Global)
│   ├── "All Accounts" view
│   ├── Filter by single account
│   ├── Filter by account type
│   └── Persist selection across pages
│
├── Account Summary Cards
│   ├── Balance per account
│   ├── Transaction count
│   ├── Last activity date
│   └── Account health indicator
│
└── Transfer View
    ├── Cross-account transfer pairs
    ├── Transfer history
    └── Unmatched transfers queue

MULTI-YEAR UI:
├── Year Selector (Global)
│   ├── Dropdown: 2024, 2025, All Time
│   ├── Custom date range
│   └── Persist selection
│
├── Year-over-Year Comparison
│   ├── Side-by-side metrics
│   ├── Growth/decline percentages
│   └── Trend charts
│
├── Historical Views
│   ├── Net worth over time (years)
│   ├── Spending trends (years)
│   ├── Income trends (years)
│   └── Category evolution
│
└── Data Management
    ├── Import by year
    ├── Archive old years
    └── Year-end rollover
```

### Effort
- Mostly UI/frontend work
- Backend already supports it
- 3-5 days estimated

---

## FEATURE 4: MANUAL ASSETS (NET WORTH) ✅ IMPLEMENTED

> **Status: IMPLEMENTED** (2025-12-28)
>
> Backend complete with full CRUD for assets and liabilities.
> - Database tables: `asset`, `liability`
> - API routes: `/api/assets/*`, `/api/liabilities/*`, `/api/networth/complete`, `/api/metals/spot`
> - Supports: real estate, vehicles, precious metals (live pricing), investments, business value
> - Frontend: /networth page (Phase 2)

### What It Does
Add non-bank assets to net worth: real estate, vehicles, precious metals, investments.

### Asset Types

```
MANUAL ASSETS:
├── Real Estate
│   ├── Property address
│   ├── Purchase price & date
│   ├── Current value (manual or Zillow API)
│   ├── Linked mortgage (liability)
│   └── Appreciation tracking
│
├── Vehicles
│   ├── Year/Make/Model/VIN
│   ├── Purchase price & date
│   ├── Current value (manual or KBB API)
│   ├── Linked auto loan (liability)
│   └── Depreciation tracking
│
├── Precious Metals
│   ├── Type: Gold, Silver, Platinum, Palladium
│   ├── Form: Coins, Bars, Rounds
│   ├── Weight (oz or grams)
│   ├── Purchase price & date
│   ├── Current value (LIVE spot price API)
│   └── Premium tracking
│
├── Investments (Manual Entry)
│   ├── 401k/IRA balances
│   ├── Brokerage accounts
│   ├── HSA balance
│   ├── Crypto holdings
│   └── Other investments
│
├── Business Value
│   ├── Business name (Mr. Patches)
│   ├── Estimated value
│   ├── Valuation method
│   └── Revenue/profit link
│
└── Other Assets
    ├── Collectibles
    ├── Equipment
    └── Custom items
```

### Database Schema

```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- real_estate, vehicle, precious_metal, investment, business, other
    subtype TEXT, -- house, car, gold, 401k, etc.
    
    -- Value tracking
    current_value REAL,
    purchase_price REAL,
    purchase_date TEXT,
    
    -- For precious metals
    weight_oz REAL,
    spot_price REAL,
    premium_paid REAL,
    
    -- For real estate/vehicles
    address TEXT,
    year_make_model TEXT,
    
    -- Liability linking
    linked_liability_id TEXT, -- link to mortgage/loan
    
    -- Metadata
    metadata JSON, -- flexible additional data
    notes TEXT,
    
    -- Auto-update settings
    auto_update BOOLEAN DEFAULT FALSE,
    update_source TEXT, -- zillow, kbb, spot_price, manual
    last_updated TEXT,
    
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE liabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- mortgage, auto_loan, personal_loan, credit_card, other
    
    original_amount REAL,
    current_balance REAL,
    interest_rate REAL,
    monthly_payment REAL,
    
    linked_asset_id TEXT, -- link to house/car
    linked_account_id TEXT, -- link to bank account for payments
    
    start_date TEXT,
    payoff_date TEXT,
    
    created_at TEXT,
    updated_at TEXT
);
```

### Live Price APIs (Free)

```python
# Precious Metals - Free APIs
METAL_APIS = {
    "gold": "https://api.metals.live/v1/spot/gold",
    "silver": "https://api.metals.live/v1/spot/silver",
    "platinum": "https://api.metals.live/v1/spot/platinum",
}

async def update_metal_prices():
    """Update all precious metal holdings with live spot prices"""
    for asset in get_assets_by_type("precious_metal"):
        spot = await fetch_spot_price(asset.subtype)
        asset.spot_price = spot
        asset.current_value = spot * asset.weight_oz
        asset.last_updated = now()
        save(asset)
```

### Net Worth Calculation

```python
def calculate_net_worth():
    # Bank accounts (existing)
    bank_total = sum(account.balance for account in get_accounts())
    
    # Manual assets (new)
    assets_total = sum(asset.current_value for asset in get_assets())
    
    # Liabilities (new)
    liabilities_total = sum(liability.current_balance for liability in get_liabilities())
    
    return {
        "bank_accounts": bank_total,
        "manual_assets": assets_total,
        "total_assets": bank_total + assets_total,
        "liabilities": liabilities_total,
        "net_worth": bank_total + assets_total - liabilities_total,
        "breakdown": {
            "real_estate": sum_by_type("real_estate"),
            "vehicles": sum_by_type("vehicle"),
            "precious_metals": sum_by_type("precious_metal"),
            "investments": sum_by_type("investment"),
            "business": sum_by_type("business"),
            "other": sum_by_type("other"),
        }
    }
```

### AI Integration
- **Financial Advisor**: Asset allocation recommendations
- **Insights Generator**: "Your gold is up 5% this month"
- **Pattern Analyzer**: Net worth growth trends

---

## FEATURE 5: AI CHAT (CHAT WITH KASHAT)

### What It Does
Natural language conversation with your financial data, powered by OpenAI API.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI CHAT FLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: "Why am I always broke?"                            │
│              │                                              │
│              ▼                                              │
│  ┌─────────────────────────────────────┐                   │
│  │     CONTEXT BUILDER                  │                   │
│  │                                      │                   │
│  │  Gathers ALL relevant data:          │                   │
│  │  • Recent transactions (500)         │                   │
│  │  • Recurring series (81)             │                   │
│  │  • P2P transactions (165)            │                   │
│  │  • Category totals                   │                   │
│  │  • Detected patterns                 │                   │
│  │  • Account balances                  │                   │
│  │  • Net worth                         │                   │
│  │  • Active insights                   │                   │
│  │  • Anomalies                         │                   │
│  └──────────────┬──────────────────────┘                   │
│                 │                                           │
│                 ▼                                           │
│  ┌─────────────────────────────────────┐                   │
│  │     OPENAI API                       │                   │
│  │                                      │                   │
│  │  Model: gpt-4o-mini (fast, cheap)    │                   │
│  │  System: "You are Kashat AI..."      │                   │
│  │  Context: [all financial data]       │                   │
│  │  User: [question]                    │                   │
│  │                                      │                   │
│  │  Cost: ~$0.01-0.05 per chat          │                   │
│  └──────────────┬──────────────────────┘                   │
│                 │                                           │
│                 ▼                                           │
│  ┌─────────────────────────────────────┐                   │
│  │     RESPONSE                         │                   │
│  │                                      │                   │
│  │  "Looking at your 2,118 transactions,│                   │
│  │   you're not actually broke..."      │                   │
│  │                                      │                   │
│  │  [Specific numbers from YOUR data]   │                   │
│  │  [Actionable recommendations]        │                   │
│  │  [Offer follow-up actions]           │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Example Queries

| Question | What AI Accesses | Response Type |
|----------|------------------|---------------|
| "Why am I broke?" | All transactions, patterns, recurring | Deep analysis + recommendations |
| "How's Mr. Patches doing?" | Business-tagged transactions | P&L summary + insights |
| "What can I deduct?" | Deductible transactions, categories | Tax prep summary |
| "Show me P2P activity" | All P2P transactions | Platform breakdown + top contacts |
| "What bills are due?" | Recurring, calendar | Upcoming bills + amounts |
| "Compare this month to last" | Monthly aggregates | Side-by-side + trends |
| "Find subscriptions I don't use" | Recurring + usage patterns | Unused list + savings |
| "Predict next month" | Patterns, recurring, history | Cash flow forecast |

### API Configuration

```python
# config.py
AI_CHAT_CONFIG = {
    "provider": "openai",  # or "anthropic", "local"
    "model": "gpt-4o-mini",  # fast and cheap
    "fallback_model": "gpt-4o",  # for complex queries
    "max_tokens": 2000,
    "temperature": 0.7,
    "context_limit": 500,  # transactions to include
}

# Cost estimate
ESTIMATED_COSTS = {
    "gpt-4o-mini": 0.01,  # per chat
    "gpt-4o": 0.05,  # per chat
    "monthly_30_chats": 0.30,  # $0.30/month
}
```

### Backend Endpoint

```python
@router.post("/api/ai/chat")
async def chat_with_kashat(request: ChatRequest):
    # Build context from all data sources
    context = await build_financial_context(
        transactions_limit=500,
        include_recurring=True,
        include_p2p=True,
        include_patterns=True,
        include_insights=True,
    )
    
    # Create system prompt
    system_prompt = create_kashat_prompt(context)
    
    # Call OpenAI
    response = await openai_client.chat.completions.create(
        model=settings.AI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
    )
    
    # Log for history
    await save_chat_history(request.message, response.choices[0].message.content)
    
    return {"response": response.choices[0].message.content}
```

### Frontend Component

```tsx
// Chat interface
function KashatChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    setLoading(true);
    const response = await fetch("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message: input }),
    });
    const data = await response.json();
    setMessages([...messages, 
      { role: "user", content: input },
      { role: "assistant", content: data.response }
    ]);
    setInput("");
    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}
      </div>
      <input 
        value={input} 
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask Kashat anything..."
      />
      <button onClick={sendMessage} disabled={loading}>
        {loading ? "Thinking..." : "Send"}
      </button>
    </div>
  );
}
```

### Cost Summary

| Usage | Model | Monthly Cost |
|-------|-------|--------------|
| Light (10 chats) | gpt-4o-mini | ~$0.10 |
| Normal (30 chats) | gpt-4o-mini | ~$0.30 |
| Heavy (100 chats) | gpt-4o-mini | ~$1.00 |
| Complex queries | gpt-4o | ~$0.05 each |

**Negligible cost for massive value.**

---

## IMPLEMENTATION ORDER

### Recommended Sequence

```
Phase 1: Foundation (Week 1-2)
├── Multi-Year/Account UI (3-5 days)
│   └── Enables proper data organization
└── Manual Assets + Liabilities (1 week)
    └── Completes net worth picture

Phase 2: Intelligence (Week 3-4)
├── Comprehensive Reports (1-2 weeks)
│   └── All data points, AI summaries
└── Integrates with existing AI modules

Phase 3: Tax & Chat (Week 5-7)
├── Tax Support (1-2 weeks)
│   └── Deductions, business split, reports
└── AI Chat (1 week)
    └── OpenAI integration, chat UI
```

### Dependencies

```
Multi-Account UI ─────┐
                      ├──► Reports ──► Tax Support
Manual Assets ────────┘                    │
                                          │
AI Modules (existing) ────────────────────┴──► AI Chat
```

---

## SUCCESS CRITERIA

### After All Features Complete

| Capability | Before | After |
|------------|--------|-------|
| Net Worth | Bank accounts only | **All assets + liabilities** |
| Reports | Basic analytics | **Comprehensive + AI insights** |
| Tax Support | None | **Full deduction tracking** |
| Multi-Year | Backend only | **Full UI support** |
| AI Interaction | Batch analysis | **Natural language chat** |

### Kashat Completeness

```
CURRENT:
├── ✅ Transaction tracking
├── ✅ Auto-categorization
├── ✅ Recurring detection (81 series)
├── ✅ P2P detection (6 platforms)
├── ✅ Transfer detection
├── ✅ Budget system
├── ✅ Bill calendar
├── ✅ Smart insights
└── ⚠️ Basic analytics only

AFTER THESE FEATURES:
├── ✅ Everything above PLUS:
├── ✅ Complete net worth (all assets)
├── ✅ Comprehensive reports (all data points)
├── ✅ Tax preparation support
├── ✅ Business expense tracking
├── ✅ Multi-year analysis
├── ✅ Natural language AI chat
└── ✅ FULL FINANCIAL PICTURE
```

---

## TOTAL EFFORT SUMMARY

| Feature | Effort | Dependencies |
|---------|--------|--------------|
| Multi-Year/Account UI | 3-5 days | None |
| Manual Assets | 1 week | None |
| Comprehensive Reports | 1-2 weeks | AI modules |
| Tax Support | 1-2 weeks | Reports |
| AI Chat | 1 week | All data sources |
| **TOTAL** | **5-7 weeks** | |

---

*These features complete the picture. Not moonshots - practical necessities.*
