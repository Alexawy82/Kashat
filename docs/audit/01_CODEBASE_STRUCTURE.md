# Codebase Structure Analysis

## Directory Tree

```
Flos/
├── apps/
│   ├── backend/                          # Python FastAPI Backend
│   │   ├── src/ledgerloop/               # Main application package
│   │   │   ├── api/                      # FastAPI application layer
│   │   │   │   ├── __init__.py           # App factory (158 lines)
│   │   │   │   ├── main.py               # Entry point (10 lines)
│   │   │   │   ├── auth.py               # Authentication
│   │   │   │   ├── errors.py             # Error handling
│   │   │   │   └── routes/               # 21 API route modules
│   │   │   │       ├── accounts.py
│   │   │   │       ├── admin.py
│   │   │   │       ├── ai.py
│   │   │   │       ├── ai_categories.py
│   │   │   │       ├── ai_enhanced.py
│   │   │   │       ├── ai_workflow.py
│   │   │   │       ├── analytics.py
│   │   │   │       ├── audit.py
│   │   │   │       ├── categories.py
│   │   │   │       ├── detect.py
│   │   │   │       ├── export.py
│   │   │   │       ├── health.py
│   │   │   │       ├── imports.py
│   │   │   │       ├── intelligence.py
│   │   │   │       ├── p2p.py
│   │   │   │       ├── recurring.py
│   │   │   │       ├── rules.py
│   │   │   │       ├── settings.py
│   │   │   │       ├── transactions.py
│   │   │   │       ├── transfers.py
│   │   │   │       └── workflows.py
│   │   │   │
│   │   │   ├── analytics/                # Analytics sub-module
│   │   │   │   └── predictive_engine.py
│   │   │   │
│   │   │   ├── detect/                   # Detection sub-module
│   │   │   │   ├── adjustments.py
│   │   │   │   ├── income.py
│   │   │   │   ├── p2p.py
│   │   │   │   └── zelle.py
│   │   │   │
│   │   │   ├── parse/                    # File parsing sub-module
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ai_parser.py
│   │   │   │   └── banks/
│   │   │   │       └── boa_v2025.py
│   │   │   │
│   │   │   ├── # Core Configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── db.py                     # Database layer (734 lines)
│   │   │   ├── logging_config.py
│   │   │   ├── metrics.py
│   │   │   ├── security.py
│   │   │   ├── settings.py
│   │   │   │
│   │   │   ├── # Core Business Logic
│   │   │   ├── cli.py                    # CLI interface (488 lines)
│   │   │   ├── dedup.py
│   │   │   ├── ingest_csv.py
│   │   │   ├── ingest_pdf.py
│   │   │   ├── normalization.py
│   │   │   ├── recurring.py
│   │   │   ├── recurring_classifier.py
│   │   │   ├── recurring_insights.py
│   │   │   ├── rules.py
│   │   │   ├── transfers.py
│   │   │   ├── p2p_detection.py
│   │   │   ├── merchant_intelligence.py
│   │   │   │
│   │   │   ├── # AI Modules (19 files)
│   │   │   ├── ai.py                     # Core AI service (1497 lines)
│   │   │   ├── ai_alerts.py
│   │   │   ├── ai_analytics.py
│   │   │   ├── ai_auto_categorization.py
│   │   │   ├── ai_categories.py
│   │   │   ├── ai_category_acceptance.py
│   │   │   ├── ai_category_schemas.py
│   │   │   ├── ai_data_quality.py
│   │   │   ├── ai_dedup.py
│   │   │   ├── ai_enhanced_categorization.py
│   │   │   ├── ai_forecasting.py
│   │   │   ├── ai_import.py
│   │   │   ├── ai_insights.py
│   │   │   ├── ai_integration.py
│   │   │   ├── ai_intelligent_dedup.py
│   │   │   ├── ai_smart_categorization.py
│   │   │   ├── ai_transfer_detection.py
│   │   │   ├── ai_workflow.py
│   │   │   ├── ingest_ai_workflow.py
│   │   │   ├── insights_ai_workflow.py
│   │   │   └── recurring_ai_workflow.py
│   │   │
│   │   ├── tests/                        # Test suite (38 files)
│   │   │   ├── conftest.py               # Pytest fixtures
│   │   │   └── test_*.py                 # Test modules
│   │   │
│   │   ├── db/                           # Database assets
│   │   │   └── migrations/               # SQL migrations
│   │   │       ├── 0001_baseline.sql
│   │   │       ├── 0002_predictive_analytics.sql
│   │   │       ├── 0003_category_normalized.sql
│   │   │       ├── 0004_workflows.sql
│   │   │       └── 0005_recurring_series_key.sql
│   │   │
│   │   └── README.md
│   │
│   └── web/                              # Next.js Frontend
│       ├── src/
│       │   ├── app/                      # Next.js App Router pages
│       │   │   ├── layout.tsx            # Root layout
│       │   │   ├── page.tsx              # Dashboard
│       │   │   ├── analytics/
│       │   │   ├── categories/
│       │   │   ├── import/
│       │   │   ├── pulse/
│       │   │   ├── recurring/
│       │   │   ├── rules/
│       │   │   ├── settings/
│       │   │   ├── transactions/
│       │   │   └── transfers/
│       │   │
│       │   ├── components/               # React components
│       │   │   ├── dashboard/            # Dashboard widgets (7)
│       │   │   ├── layout/               # Layout components
│       │   │   ├── ui/                   # shadcn/ui primitives (19)
│       │   │   └── providers.tsx
│       │   │
│       │   ├── hooks/                    # Custom React hooks (13)
│       │   │   ├── useAccounts.ts
│       │   │   ├── useAIQueue.ts
│       │   │   ├── useAnalytics.ts
│       │   │   ├── useAutomation.ts
│       │   │   ├── useCategories.ts
│       │   │   ├── useDebounce.ts
│       │   │   ├── useImports.ts
│       │   │   ├── useIntelligence.ts
│       │   │   ├── useP2P.ts
│       │   │   ├── usePulse.ts
│       │   │   ├── useRecurring.ts
│       │   │   ├── useSettings.ts
│       │   │   └── useTransactions.ts
│       │   │
│       │   ├── lib/                      # Utilities
│       │   │   ├── api/                  # Generated API client
│       │   │   ├── api-client.ts
│       │   │   └── utils.ts
│       │   │
│       │   ├── types/                    # TypeScript types
│       │   │   └── domain.ts
│       │   │
│       │   └── __tests__/                # Frontend tests
│       │
│       ├── e2e/                          # Playwright e2e tests
│       │   └── flows.spec.ts
│       │
│       ├── package.json
│       ├── tsconfig.json
│       ├── tailwind.config.js
│       ├── next.config.js
│       ├── openapi-ts.config.ts
│       ├── playwright.config.ts
│       └── openapi.json                  # OpenAPI spec (235KB)
│
├── scripts/                              # Utility scripts
│   ├── dev_up.sh
│   ├── dev_down.sh
│   ├── smoke_test.py
│   ├── bootstrap_categories.py
│   ├── determinism_check.py
│   └── [20+ other scripts]
│
├── docs/                                 # Documentation
│   └── audit/                            # This audit
│
├── bank/                                 # Bank statement fixtures
│
├── # Configuration Files
├── docker-compose.yml
├── docker-compose.corelab.yml
├── Dockerfile.backend
├── Dockerfile.web
├── Makefile
├── pytest.ini
├── requirements.txt
├── .coveragerc
├── .env.example
├── .env.corelab
├── .gitignore
├── README.md
└── CONTRIBUTING.md
```

---

## File Inventory

### Backend Python Files

| Category | File | Lines | Purpose |
|----------|------|-------|---------|
| **Core** | db.py | 734 | SQLite connection, schema, migrations |
| **Core** | config.py | ~100 | Configuration and paths |
| **Core** | cli.py | 488 | Command-line interface |
| **Core** | logging_config.py | ~50 | Logging setup |
| **Core** | metrics.py | ~150 | Prometheus metrics |
| **Core** | security.py | ~100 | Security utilities |
| **Core** | settings.py | ~100 | Settings management |
| **API** | api/__init__.py | 158 | App factory, middleware |
| **API** | api/main.py | 10 | Entry point |
| **API** | api/auth.py | ~200 | JWT authentication |
| **API** | api/errors.py | ~100 | Exception handlers |
| **Routes** | routes/transactions.py | ~400 | Transaction CRUD |
| **Routes** | routes/imports.py | ~500 | File import |
| **Routes** | routes/analytics.py | ~400 | Analytics endpoints |
| **Routes** | routes/recurring.py | ~600 | Recurring detection |
| **Routes** | routes/transfers.py | ~400 | Transfer matching |
| **Routes** | routes/ai.py | ~600 | AI operations |
| **Routes** | routes/admin.py | ~500 | Admin operations |
| **Routes** | routes/[others] | ~2000 | Other endpoints |
| **AI** | ai.py | 1497 | Core AI service |
| **AI** | ai_workflow.py | 510 | Workflow automation |
| **AI** | ai_auto_categorization.py | 795 | Auto-categorization |
| **AI** | merchant_intelligence.py | 697 | Merchant analysis |
| **AI** | [16 other ai_*.py] | ~3000 | Specialized AI |
| **Logic** | recurring.py | ~400 | Recurring detection |
| **Logic** | transfers.py | ~300 | Transfer detection |
| **Logic** | rules.py | ~250 | Rule engine |
| **Logic** | dedup.py | ~150 | Deduplication |
| **Logic** | normalization.py | ~200 | Text normalization |
| **Import** | ingest_csv.py | ~300 | CSV import |
| **Import** | ingest_pdf.py | ~200 | PDF import |
| **Detect** | detect/zelle.py | ~100 | Zelle detection |
| **Detect** | detect/p2p.py | ~100 | P2P detection |
| **Detect** | detect/income.py | ~100 | Income detection |
| **Detect** | detect/adjustments.py | ~100 | Adjustment detection |
| **Parse** | parse/ai_parser.py | ~300 | AI PDF parsing |
| **Parse** | parse/banks/boa_v2025.py | ~400 | BoA parser |
| **Tests** | tests/test_*.py (38 files) | ~5000 | Test suite |

**Total Backend:** ~15,000+ lines

---

### Frontend TypeScript/React Files

| Category | File | Purpose |
|----------|------|---------|
| **Pages** | app/page.tsx | Dashboard |
| **Pages** | app/analytics/page.tsx | Analytics |
| **Pages** | app/transactions/page.tsx | Transaction list |
| **Pages** | app/categories/page.tsx | Categories |
| **Pages** | app/import/page.tsx | File import |
| **Pages** | app/recurring/page.tsx | Recurring payments |
| **Pages** | app/transfers/page.tsx | Transfers |
| **Pages** | app/rules/page.tsx | Rules |
| **Pages** | app/pulse/page.tsx | System health |
| **Pages** | app/settings/*.tsx | Settings pages |
| **Dashboard** | components/dashboard/HealthScoreCard.tsx | Health widget |
| **Dashboard** | components/dashboard/RunwayCard.tsx | Runway widget |
| **Dashboard** | components/dashboard/IntelligenceFeed.tsx | AI insights |
| **Dashboard** | components/dashboard/[4 more] | Other widgets |
| **Layout** | components/layout/Sidebar.tsx | Navigation |
| **Layout** | components/layout/CommandPalette.tsx | Cmd+K search |
| **UI** | components/ui/*.tsx (19 files) | shadcn primitives |
| **Hooks** | hooks/useTransactions.ts | Transaction API |
| **Hooks** | hooks/useCategories.ts | Category API |
| **Hooks** | hooks/useAnalytics.ts | Analytics API |
| **Hooks** | hooks/[10 more] | Other hooks |
| **Lib** | lib/api-client.ts | HTTP client |
| **Lib** | lib/utils.ts | Utilities |
| **Types** | types/domain.ts | Domain types |

**Total Frontend:** ~10,000+ lines

---

## Architecture Pattern

### Pattern: Layered Architecture with AI-First Design

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI HTTP Layer                       │
│          (21 route modules in api/routes/)                  │
├─────────────────────────────────────────────────────────────┤
│                  Business Logic Layer                       │
│  ┌──────────────────┬──────────────┬──────────────────────┐ │
│  │  Data Import     │   Financial  │   AI Modules (19)    │ │
│  │  ─────────────   │   Analysis   │   ──────────────────│ │
│  │ • ingest_csv     │  ──────────  │  • ai.py (core)     │ │
│  │ • ingest_pdf     │ • transfers  │  • ai_workflow      │ │
│  │ • normalization  │ • recurring  │  • ai_categories    │ │
│  │ • dedup          │ • rules      │  • 16+ specialized  │ │
│  └──────────────────┴──────────────┴──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│              Detection & Parsing Sub-modules                │
│  ┌────────────────────┐        ┌──────────────────────────┐ │
│  │ detect/            │        │ parse/                   │ │
│  │ • income.py        │        │ • ai_parser.py           │ │
│  │ • p2p.py           │        │ • banks/boa_v2025.py     │ │
│  │ • adjustments.py   │        └──────────────────────────┘ │
│  │ • zelle.py         │                                     │
│  └────────────────────┘                                     │
├─────────────────────────────────────────────────────────────┤
│                  Data Access Layer (SQLite)                 │
│              db.py (connection pool, schema)                │
├─────────────────────────────────────────────────────────────┤
│            Persistent Storage (SQLite WAL Mode)             │
│  • transaction, account, category, rules                    │
│  • match_transfer, recurring_series                         │
│  • import_run, event_log                                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Patterns

1. **Modular AI Suite:** 19 dedicated AI modules with clear responsibilities
2. **Provider Abstraction:** AI providers can be swapped (OpenAI, LM Studio, local)
3. **Workflow Engine:** Pipeline orchestration for complex multi-step processes
4. **Event Sourcing:** Complete audit trail via event_log table
5. **Rule Engine:** Regex-based rule system for automatic categorization
6. **Fingerprinting:** SHA1-based deduplication across imports

### Consistency Assessment

| Aspect | Consistent? | Notes |
|--------|-------------|-------|
| Naming Conventions | Mostly | snake_case Python, camelCase JS |
| Error Handling | Yes | Centralized error handlers |
| API Response Format | Yes | Consistent JSON structure |
| Database Access | Yes | Via get_conn() wrapper |
| Logging | Partial | Some modules missing logging |
| Type Hints | Partial | ~70% coverage |

### Deviations

1. **AI Module Overlap:** Multiple categorization modules (ai_categories.py, ai_enhanced_categorization.py, ai_smart_categorization.py) with overlapping functionality

2. **Inconsistent Caching:** Some routes use @lru_cache, others don't cache at all

3. **Mixed Test Patterns:** Some tests use unittest.TestCase, others use pytest fixtures

---

## Entry Points

### 1. API Entry Point
- **File:** `apps/backend/src/ledgerloop/api/main.py`
- **Usage:** `uvicorn ledgerloop.api.main:app --reload`

### 2. CLI Entry Point
- **File:** `apps/backend/src/ledgerloop/cli.py`
- **Commands:** ingest, stats, classify, detect, export, health

### 3. Frontend Entry Point
- **File:** `apps/web/src/app/layout.tsx`
- **Usage:** `npm run dev` or `next start`

---

*Generated by Claude Code Audit - December 27, 2025*
