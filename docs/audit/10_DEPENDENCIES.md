# Dependencies Documentation

## Backend Dependencies (Python)

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.0 | Modern async web framework |
| uvicorn | 0.37.0 | ASGI server |
| gunicorn | 22.0.0 | Production server wrapper |

### Database

| Package | Version | Purpose |
|---------|---------|---------|
| duckdb | 1.1.3 | Embedded analytical database |

**Note:** The codebase uses SQLite (stdlib) as the primary database, with DuckDB available for analytical queries.

### AI/ML

| Package | Version | Purpose |
|---------|---------|---------|
| openai | 1.51.0 | OpenAI API client |
| numpy | 1.26.4 | Numerical computing |

### Data Processing

| Package | Version | Purpose |
|---------|---------|---------|
| pyarrow | 16.1.0 | Columnar data, Parquet export |
| pdfplumber | 0.11.4 | PDF text extraction |

### HTTP & Networking

| Package | Version | Purpose |
|---------|---------|---------|
| requests | 2.32.3 | HTTP client (sync) |
| httpx | 0.27.2 | HTTP client (async) |

### Authentication & Security

| Package | Version | Purpose |
|---------|---------|---------|
| python-jose[cryptography] | 3.3.0 | JWT token handling |
| passlib[bcrypt] | 1.7.4 | Password hashing |

### Configuration

| Package | Version | Purpose |
|---------|---------|---------|
| python-dotenv | 1.0.1 | Environment variable loading |
| python-multipart | 0.0.9 | Multipart form data |

### Monitoring

| Package | Version | Purpose |
|---------|---------|---------|
| prometheus-client | 0.20.0 | Prometheus metrics |
| slowapi | 0.1.9 | Rate limiting |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.2.1 | Test framework |
| pytest-cov | 5.0.0 | Coverage reporting |
| pytest-asyncio | 0.23.8 | Async test support |

---

## Frontend Dependencies (Node.js)

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| next | 14.2.35 | React meta-framework |
| react | 18.2.0 | UI library |
| react-dom | 18.2.0 | React DOM rendering |

### State Management

| Package | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-query | 5.90.12 | Server state management |
| zustand | 5.0.0 | Client state (unused) |

### API Client

| Package | Version | Purpose |
|---------|---------|---------|
| @hey-api/client-fetch | 0.13.1 | Fetch-based HTTP client |
| @hey-api/openapi-ts | 0.89.2 | OpenAPI code generation |

### UI Components (Radix UI)

| Package | Version | Purpose |
|---------|---------|---------|
| @radix-ui/react-checkbox | 1.3.3 | Checkbox |
| @radix-ui/react-dialog | 1.1.15 | Modal dialogs |
| @radix-ui/react-dropdown-menu | 2.1.16 | Dropdown menus |
| @radix-ui/react-label | 2.1.8 | Form labels |
| @radix-ui/react-progress | 1.1.8 | Progress bars |
| @radix-ui/react-select | 2.2.6 | Select dropdowns |
| @radix-ui/react-separator | 1.1.8 | Separators |
| @radix-ui/react-slider | 1.3.6 | Range sliders |
| @radix-ui/react-slot | 1.2.4 | Slot component |
| @radix-ui/react-switch | 1.2.6 | Toggle switches |
| @radix-ui/react-tabs | 1.1.13 | Tab components |

### Data Display

| Package | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-table | 8.21.3 | Headless table |
| recharts | 3.2.1 | Charts |
| react-window | 1.8.9 | Virtual scrolling |

### Styling

| Package | Version | Purpose |
|---------|---------|---------|
| tailwindcss | 3.4.17 | Utility CSS |
| tailwindcss-animate | 1.0.7 | Animations |
| class-variance-authority | 0.7.1 | Variant classes |
| clsx | 2.1.1 | Class merging |
| tailwind-merge | 3.4.0 | Tailwind class dedup |

### UI Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| lucide-react | 0.544.0 | Icons |
| cmdk | 1.1.1 | Command palette |

### Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| typescript | 5.9.3 | Type checking |
| @types/node | 24.6.0 | Node.js types |
| @types/react | 19.1.15 | React types |
| autoprefixer | 10.4.21 | CSS prefixing |
| postcss | 8.5.6 | CSS processing |

---

## Dependency Graph

### Backend Module Dependencies

```
api/
├── routes/* -> business logic modules
│   ├── transactions.py -> db.py
│   ├── imports.py -> ingest_csv.py, ingest_pdf.py
│   ├── recurring.py -> recurring.py, recurring_classifier.py
│   ├── transfers.py -> transfers.py
│   └── ai.py -> ai.py, ai_workflow.py

business logic/
├── recurring.py -> db.py, normalization.py
├── transfers.py -> db.py
├── rules.py -> db.py
├── ingest_csv.py -> normalization.py, dedup.py
└── ingest_pdf.py -> parse/ai_parser.py, parse/banks/

ai/
├── ai.py (core) -> openai, settings
├── ai_workflow.py -> ai.py, db.py
├── ai_auto_categorization.py -> ai.py, merchant_intelligence.py
└── ai_*.py -> ai.py
```

### Frontend Module Dependencies

```
app/
├── layout.tsx -> providers.tsx, Sidebar.tsx
├── page.tsx -> dashboard/*
├── transactions/ -> useTransactions, DataTable
├── recurring/ -> useRecurring, components/*
└── transfers/ -> useP2P, components/*

hooks/
├── useTransactions.ts -> api-client.ts
├── useCategories.ts -> api-client.ts
├── useRecurring.ts -> api-client.ts
└── use*.ts -> @tanstack/react-query

lib/
├── api-client.ts -> fetch API
└── api/ (generated) -> @hey-api/client-fetch
```

---

## Bundle Size Impact (Frontend)

| Package | Estimated Size | Impact |
|---------|---------------|--------|
| react + react-dom | ~130KB | Core |
| next | ~80KB (runtime) | Framework |
| @tanstack/react-query | ~30KB | State |
| recharts | ~150KB | Charts |
| @tanstack/react-table | ~40KB | Tables |
| Radix UI (all) | ~50KB | Components |
| lucide-react | ~5KB (tree-shaken) | Icons |
| tailwindcss | 0KB (build-time) | Styling |

**Total Estimated:** ~500KB (gzipped: ~150KB)

---

## Security Vulnerabilities

### Known Issues (as of audit date)

None detected in current versions.

### Recommendations

1. **Keep dependencies updated** - Run `npm audit` and `pip-audit` regularly
2. **Pin versions** - Use exact versions in production
3. **Monitor advisories** - Subscribe to security advisories for critical packages

---

## Alternative Packages

### Backend

| Current | Alternative | Notes |
|---------|-------------|-------|
| duckdb | SQLite (stdlib) | Already using SQLite primarily |
| pdfplumber | PyMuPDF | Faster but GPL licensed |
| openai | anthropic | For Claude models |
| slowapi | fastapi-limiter | Similar functionality |

### Frontend

| Current | Alternative | Notes |
|---------|-------------|-------|
| @tanstack/react-query | SWR | Smaller, less features |
| recharts | visx | More customizable |
| zustand | jotai, recoil | Different paradigms |
| cmdk | kbar | Alternative command palette |

---

## Unused Dependencies

### Frontend

- **zustand** - Installed but not imported anywhere
  - Recommendation: Remove or start using for client-only state

---

## Update Strategy

### Patch Updates (X.Y.Z -> X.Y.Z+1)

Safe to update automatically. Run tests after update.

### Minor Updates (X.Y -> X.Y+1)

Review changelog for breaking changes. Test thoroughly.

### Major Updates (X -> X+1)

Requires careful planning:
- Review migration guide
- Update code as needed
- Full regression testing

### Critical Packages to Monitor

| Package | Reason |
|---------|--------|
| fastapi | Core framework, breaking changes rare |
| next | Major versions every 6 months |
| openai | API changes affect prompts |
| react | Major versions are significant |

---

*Generated by Claude Code Audit - December 27, 2025*
