# Kashat - كاشات

**Your money, your data, your rules.**
**كاشاتك، بياناتك، قواعدك**

A comprehensive, privacy-centric personal finance application with AI-powered insights. All your data stays local - no cloud storage, no external services, complete control over your financial data.

## Project Status: Production Ready

**Version:** 2.0.0 | **Last Updated:** December 27, 2025

Kashat is feature-complete with a robust FastAPI backend, modern Next.js frontend, and intelligent AI-powered transaction analysis.

---

## Features

### Core Functionality
- **Multi-format Import**: CSV files and PDF statements (Bank of America supported with AI vision)
- **Smart Deduplication**: Prevents duplicate transactions across re-imports
- **Auto-categorization**: Powerful rule engine with regex and amount conditions
- **Transfer Detection**: Identifies internal account transfers automatically
- **Recurring Detection**: Finds subscription and recurring payment patterns
- **P2P Detection**: Identifies person-to-person transfers (Zelle, Venmo, CashApp, PayPal, Wire, Western Union) with counterparty tracking
- **Net Worth Tracking**: Real-time asset and liability calculation across all accounts
- **Budget System**: Category-based budgets with progress tracking and rollover support
- **Bill Calendar**: Visual calendar showing upcoming bills and payment due dates
- **Transaction Review**: Mark transactions as reviewed with bulk operations

### AI-Powered Intelligence
- **Financial Health Score**: Overall health assessment with component scores
- **Spending Behavior Analysis**: Persona detection, patterns, risk factors
- **Smart Insight Cards**: Spending spikes, price increases, unused subscriptions
- **Personalized Insights**: AI-generated recommendations and alerts
- **Anomaly Detection**: Unusual spending pattern identification
- **Merchant Memory**: Learn and remember merchant categorizations
- **Smart Categorization**: AI-assisted transaction classification
- **PDF Vision Parsing**: OpenAI vision for bank statement extraction

### Analytics & Reporting
- **Unified Dashboard**: Overview, Spending, Trends, Forecast tabs
- **Custom Date Ranges**: Filter and analyze any time period
- **Spending Insights**: Category breakdowns and spending patterns
- **Cash Flow Analysis**: Income vs expenses with adjustment handling

### Modern UI
- **Streamlined Navigation**: 6 main sections for focused workflow
- **Settings Hub**: Categories, Automation, System status in one place
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Bulk Operations**: Update multiple transactions simultaneously

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) OpenAI API key or LMStudio for AI features

### Development Setup

```bash
# Clone and setup
git clone <repo-url>
cd Flos

# Backend setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd apps/web
npm install
cd ../..

# Start backend
source .venv/bin/activate
export PYTHONPATH=apps/backend/src
export KASHAT_DATA_DIR=./data
export KASHAT_CORS="*"
uvicorn kashat.api.main:app --host 127.0.0.1 --port 8000

# Start frontend (new terminal)
cd apps/web
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000/api"
npm run dev -- -p 3000
```

### Access
- **Frontend**: http://127.0.0.1:3000
- **Backend API**: http://127.0.0.1:8000/api
- **API Docs**: http://127.0.0.1:8000/docs

---

## Application Structure

### Navigation (8 Main Sections)

| Section | Route | Description |
|---------|-------|-------------|
| **Dashboard** | `/` | Unified view with 4 tabs: Overview, Spending, Trends, Forecast |
| **Transactions** | `/transactions` | Transaction list with filters, bulk operations |
| **Import** | `/import` | File upload for CSV and PDF statements |
| **Calendar** | `/calendar` | Bill calendar with upcoming payments |
| **Budget** | `/budget` | Budget management with category limits |
| **Recurring** | `/recurring` | Subscriptions and recurring payment management |
| **Transfers** | `/transfers` | P2P detection, counterparties, internal transfers |
| **Analytics** | `/analytics` | Detailed analytics and financial insights |

### Settings Sub-sections

| Sub-section | Route | Description |
|-------------|-------|-------------|
| General | `/settings` | AI configuration, app preferences |
| Categories | `/settings/categories` | Category CRUD, AI gap analysis |
| Automation | `/settings/automation` | Rules engine, AI suggestions |
| System | `/settings/system` | Health status, logs, diagnostics |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KASHAT_DATA_DIR` | `~/.kashat` | Data directory for database |
| `KASHAT_CORS` | - | CORS origins (use `*` for dev) |
| `NEXT_PUBLIC_API_BASE` | - | Backend URL for frontend |
| `OPENAI_API_KEY` | - | OpenAI API key for AI features |
| `KASHAT_AI_LMSTUDIO_BASE_URL` | - | LMStudio URL (alternative to OpenAI) |

---

## Project Structure

```
Kashat/
├── apps/
│   ├── backend/                 # FastAPI application
│   │   ├── src/kashat/
│   │   │   ├── api/            # API routes
│   │   │   │   └── routes/     # Route modules
│   │   │   ├── detect/         # Detection algorithms
│   │   │   ├── parse/          # Bank statement parsers
│   │   │   ├── ai/             # AI modules
│   │   │   └── *.py            # Core modules
│   │   └── tests/              # Test suite
│   └── web/                    # Next.js frontend
│       └── src/
│           ├── app/            # Page routes
│           ├── components/     # UI components
│           ├── hooks/          # React Query hooks
│           └── lib/            # Utilities
├── bank/                       # Bank statements (gitignored)
├── data/                       # Database (gitignored)
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
└── requirements.txt            # Python dependencies
```

---

## API Overview

### 150+ Endpoints

| Category | Prefix | Description |
|----------|--------|-------------|
| Transactions | `/api/transactions` | CRUD, bulk operations, filtering, review |
| Categories | `/api/categories` | Category management |
| Rules | `/api/rules` | Rule engine, apply rules |
| Recurring | `/api/recurring` | Recurring detection & management |
| Transfers | `/api/transfers` | Internal transfer detection |
| P2P | `/api/p2p` | P2P detection, counterparties |
| Analytics | `/api/analytics` | Summary, monthly, trends |
| Intelligence | `/api/intelligence` | AI insights, health score |
| AI | `/api/ai` | Categorization, merchant memory |
| Imports | `/api/imports` | File upload, parse, runs |
| Export | `/api/export` | CSV, Parquet export |
| Admin | `/api/admin` | Backup, restore, reset |
| Health | `/api/health` | Status, detailed diagnostics |
| Net Worth | `/api/networth` | Asset/liability calculation, snapshots |
| Calendar | `/api/calendar` | Upcoming bills, monthly view |
| Budgets | `/api/budgets` | Budget CRUD, progress tracking |
| Insights | `/api/insights` | Smart insight cards |

---

## AI Features

### Providers Supported
- **OpenAI**: GPT-4o-mini (default), GPT-4o for vision
- **LMStudio**: Local models via API compatibility

### AI Capabilities
- Transaction categorization with confidence scoring
- Context-aware classification
- Spending analysis and forecasting
- Trend prediction
- Personalized recommendations
- Anomaly detection
- Intelligent deduplication
- Merchant normalization

---

## Testing

```bash
# Backend tests
source .venv/bin/activate
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests -v

# Frontend type checking
cd apps/web
npm run build
```

---

## Production Deployment

### Docker
```bash
docker-compose up -d
```

### Environment
```bash
export KASHAT_DATA_DIR=/path/to/data
export KASHAT_CORS="https://your-domain.com"
export OPENAI_API_KEY="your-api-key"
```

See `docs/DEPLOYMENT.md` for detailed instructions.

---

## Monitoring

- **Health Check**: `GET /api/health`
- **Detailed Health**: `GET /api/health/detailed`
- **Prometheus Metrics**: `GET /metrics`

---

## Known Limitations

1. **Single-user mode**: Designed for personal use
2. **SQLite single-writer**: One backend process at a time
3. **Local-first**: No cloud sync by design

---

## Contributing

See `CONTRIBUTING.md` for development guidelines.

---

## License

Private - All rights reserved.

---

**Privacy First**: All data remains on your local machine. No cloud services, no data sharing, complete control over your financial information.
