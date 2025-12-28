# KASHAT - Unified Development Roadmap
## From LedgerLoop Audit → Kashat v2.0

**Date**: December 27, 2025  
**Prepared for**: Marwan  
**Context**: Finance module for Life OS ecosystem

---

## Executive Summary

### What Claude's Audit Found

| Metric | Value | Assessment |
|--------|-------|------------|
| **Total Code** | ~66,500 lines | Substantial app |
| **Backend Modules** | 75+ Python files | Well-organized |
| **API Endpoints** | 150+ routes | Comprehensive |
| **Database Tables** | 25+ tables | Solid schema |
| **AI Modules** | 19 modules | **Needs consolidation** |
| **Test Coverage** | 45% | Below target |

### Top Issues by Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| **P0** | JWT secret hardcoded | 1 hour | CRITICAL |
| **P0** | CORS too permissive | 30 min | CRITICAL |
| **P0** | Admin endpoints unprotected | 30 min | CRITICAL |
| **P1** | Missing database indexes | 1 hour | HIGH |
| **P1** | N+1 query patterns | 4 hours | HIGH |
| **P1** | No rate limiting on AI | 1 hour | HIGH |
| **P2** | 19 AI modules → consolidate to 6 | 2-3 days | MEDIUM |
| **P2** | Test coverage 45% → 70% | 1 week | MEDIUM |

---

## Part 1: The Rename - LedgerLoop → Kashat

### Files to Update

```
[ ] package.json (name field)
[ ] apps/web/package.json
[ ] apps/backend/pyproject.toml
[ ] docker-compose.yml (service names)
[ ] README.md
[ ] docs/*.md (all documentation)
[ ] apps/web/src/app/layout.tsx (title)
[ ] apps/web/public/manifest.json (if PWA)
[ ] Any hardcoded "LedgerLoop" strings
[ ] Browser tab title
[ ] API routes (if /ledgerloop/ in path)
```

### Branding

```
Kashat
كاشاتك، بياناتك، قواعدك
Your money, your data, your rules.
```

**Effort**: 2-3 hours

---

## Part 2: Security Fixes (P0 - Do First)

### 1. JWT Secret Generation (1 hour)

```python
# api/security.py
import secrets
from pathlib import Path

def get_or_create_jwt_secret():
    secret_file = data_dir() / ".jwt_secret"
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    secret = secrets.token_urlsafe(32)
    secret_file.write_text(secret)
    return secret

JWT_SECRET = get_or_create_jwt_secret()
```

### 2. CORS Restriction (30 min)

```python
# api/__init__.py
allowed_origins = os.getenv("KASHAT_CORS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Not "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Production Mode Check (30 min)

```python
@app.on_event("startup")
async def check_security():
    if os.getenv("KASHAT_ENV") == "production":
        if "dev-secret" in os.getenv("KASHAT_JWT_SECRET", ""):
            raise RuntimeError("Production requires unique JWT secret")
```

---

## Part 3: Performance Fixes (P1 - This Week)

### 1. Database Indexes (1 hour)

```sql
-- migrations/0007_performance_indexes.sql
CREATE INDEX IF NOT EXISTS idx_tx_ai_processed ON [transaction](ai_processed_at);
CREATE INDEX IF NOT EXISTS idx_tx_is_business ON [transaction](is_business);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transaction_category(category_id);
CREATE INDEX IF NOT EXISTS idx_mcm_merchant ON merchant_category_mapping(merchant_name);
CREATE INDEX IF NOT EXISTS idx_recurring_next ON recurring_series(next_date);
```

### 2. Fix N+1 Queries (4 hours)

**Before:**
```python
for tx in transactions:
    tx.category_name = get_category_name(tx.category_id)  # N queries!
```

**After:**
```python
category_ids = {tx.category_id for tx in transactions if tx.category_id}
categories = {c.id: c.name for c in get_categories_by_ids(category_ids)}
for tx in transactions:
    tx.category_name = categories.get(tx.category_id)
```

### 3. Rate Limiting on AI (1 hour)

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/analyze/bulk")
@limiter.limit("10/minute")
async def analyze_bulk(request: Request, ...):
    ...
```

---

## Part 4: AI Module Consolidation (P2)

### Current State: 19 Modules with Overlap

| Module Group | Files | Problem |
|--------------|-------|---------|
| Categorization | ai_categories.py, ai_enhanced_categorization.py, ai_smart_categorization.py, ai_auto_categorization.py | 4 files doing same thing |
| Deduplication | ai_dedup.py, ai_intelligent_dedup.py | 2 files overlap |
| Workflows | ai_workflow.py, ingest_ai_workflow.py, insights_ai_workflow.py | 3 workflow files |

### Target State: 6 Consolidated Modules

```
ai/
├── __init__.py          # Public API
├── core.py              # AIService, providers, config
├── categorization.py    # ALL categorization logic
├── detection.py         # Transfer, P2P, recurring
├── quality.py           # Data quality, dedup
├── workflows.py         # All pipeline orchestration
└── prompts.py           # All prompt templates
```

**Effort**: 2-3 days

---

## Part 5: Features Gap - What Competitors Have

### From Our Research (Albert, Rocket Money, Monarch)

| Feature | Have? | Priority | Effort |
|---------|-------|----------|--------|
| **Net Worth View** | ❌ | HIGH | 1 day |
| **Bill Calendar** | ❌ | HIGH | 1 day |
| **Budget System** | ❌ | HIGH | 3-5 days |
| **Smart Insight Cards** | ⚠️ Data exists | HIGH | 2 days |
| **Transaction Review Flag** | ❌ | MEDIUM | 2 hours |
| **Cash Flow Forecast** | ⚠️ Partial | MEDIUM | 2 days |
| **Spending vs Average** | ❌ | MEDIUM | 1 day |
| **Subscription Health** | ⚠️ Partial | LOW | 1 day |

### Quick Wins (Use Existing Data)

**1. Net Worth View**
```
Assets (checking, savings) - Liabilities (credit cards) = Net Worth
Just need UI + account type field
```

**2. Bill Calendar**
```
recurring_series already has: next_date, amount_mean, name
Just need calendar UI component
```

**3. Smart Insight Cards**
```sql
-- Spending spike detection (data already exists!)
SELECT c.name, 
       SUM(CASE WHEN month = current THEN amount END) as current_month,
       AVG(monthly_spend) as average
FROM transactions
GROUP BY category
HAVING current_month > average * 1.3;
```

---

## Part 6: The Vision - Kashat Agent (v2.0)

### Architecture (From Our Discussion)

```
┌─────────────────────────────────────────────────────────┐
│                      KASHAT (Tool)                       │
│         All features • Full UI • All power               │
│                                                          │
│   Import │ Transactions │ Analytics │ Rules │ Budget    │
│                          ▲                               │
│                          │ API (150+ endpoints)          │
│   ┌──────────────────────┴──────────────────────┐        │
│   │            🤖 KASHAT AGENT                   │        │
│   │                                              │        │
│   │   • Watches for new statements               │        │
│   │   • Uploads & processes automatically        │        │
│   │   • Runs categorization workflows            │        │
│   │   • Extracts key insights                    │        │
│   │   • Reports to Life OS                       │        │
│   └──────────────────────┬──────────────────────┘        │
└──────────────────────────┼──────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │      LIFE OS HUB       │
              │                        │
              │  💰 Kashat says:       │
              │  "December processed.  │
              │   Spending up 12%."    │
              │                        │
              │  [Chat] [Open Kashat]  │
              └────────────────────────┘
```

### Implementation (Phase 2)

```python
# Using Ollama (local) + LangChain
from langchain_community.llms import Ollama
from langchain.agents import create_sql_agent

llm = Ollama(model="llama3")  # Runs locally, FREE

# Agent can query your DuckDB directly
agent = create_sql_agent(
    llm=llm,
    db=kashat_db_connection,
)

# Natural language queries
agent.run("Why am I broke this month?")
agent.run("What subscriptions am I not using?")
agent.run("Can I afford a $500 purchase?")
```

**Effort**: 1-2 weeks (after core fixes)

---

## Part 7: Unified Roadmap

### Week 1: Security & Stability
| Day | Task | Owner |
|-----|------|-------|
| 1 | Rename to Kashat | Claude |
| 1 | JWT secret fix (P0) | Claude |
| 1 | CORS restriction (P0) | Claude |
| 2 | Database indexes (P1) | Claude |
| 3 | N+1 query fixes (P1) | Claude |
| 4 | Rate limiting (P1) | Claude |
| 5 | Error standardization | Claude |

### Week 2: Features
| Day | Task | Owner |
|-----|------|-------|
| 6 | Net Worth View | Claude |
| 7 | Bill Calendar UI | Claude |
| 8 | Smart Insight Cards | Claude |
| 9 | Transaction Review Flag | Claude |
| 10 | Cash Flow Forecast | Claude |

### Week 3: AI Consolidation
| Day | Task | Owner |
|-----|------|-------|
| 11-12 | Consolidate 19 AI modules → 6 | Claude |
| 13 | Update all imports/references | Claude |
| 14 | Test AI fallback behavior | Claude |
| 15 | Documentation update | Claude |

### Week 4: Budget System
| Day | Task | Owner |
|-----|------|-------|
| 16 | Design budget tables | Claude |
| 17 | Budget CRUD API | Claude |
| 18 | Budget UI (progress bars) | Claude |
| 19 | Budget rollover logic | Claude |
| 20 | Integration testing | Claude |

### Month 2: Agent Layer (v2.0)
| Week | Task |
|------|------|
| 5 | Chat interface UI |
| 6 | Ollama integration |
| 6 | Agent tool definitions |
| 7 | Natural language queries |
| 8 | Life OS connector |

---

## Part 8: Success Metrics

| Metric | Current | Target | When |
|--------|---------|--------|------|
| Security vulnerabilities | 3 | 0 | Week 1 |
| API response time | ~200ms | <100ms | Week 2 |
| AI modules | 19 | 6 | Week 3 |
| Test coverage | 45% | 70% | Month 1 |
| Features vs competitors | 70% | 95% | Month 1 |
| Agent integration | 0% | 100% | Month 2 |

---

## Part 9: What NOT to Build

Based on our research, these are **out of scope**:

| Feature | Why Skip |
|---------|----------|
| Bill negotiation | Requires BillShark partnership |
| Subscription cancellation | Requires manual human service |
| Credit score | Requires Experian API (expensive) |
| Bank API sync | Requires Plaid ($$$), defeats privacy |
| Cash advances | Requires banking license |
| Multi-user | Single-user Life OS is the vision |

---

## Part 10: Kashat's Competitive Advantage

### What Makes Kashat Unique

| Feature | Albert | Rocket Money | Kashat |
|---------|--------|--------------|--------|
| **Price** | $15-40/mo | $6-12/mo | **FREE** |
| **Privacy** | Cloud | Cloud | **LOCAL** |
| **Bank Sync Required** | Yes | Yes | **NO** |
| **Custom Rules** | No | No | **YES** |
| **Transfer Detection** | No | No | **3 algorithms** |
| **AI Modules** | Basic | Basic | **19 → 6 consolidated** |
| **Agent Integration** | No | No | **Planned v2.0** |
| **Open Architecture** | No | No | **150+ APIs** |

### Positioning

> **Kashat**: The only local-first, AI-powered, privacy-focused personal finance app with statement import (no bank API required), custom automation rules, and future agent integration for your Life OS.

---

## Decision Points for Marwan

### Immediate Questions:

1. **Start with rename?** 
   - Do Kashat rename in Week 1 or save for later?

2. **Security fixes first?**
   - P0 fixes before features, or parallel?

3. **AI consolidation timing?**
   - Week 3 as planned, or defer?

4. **Budget system priority?**
   - Essential for v1.0 or nice-to-have?

5. **Agent layer timeline?**
   - Start Month 2 or wait for Life OS foundation?

---

*Ready to execute. What's your call?*
