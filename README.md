<div align="center">

# Kashat

### The Privacy-First Personal Finance Platform

**AI-Powered Intelligence • Self-Hosted • 100% Free Forever**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Vibe Coded](https://img.shields.io/badge/Built%20With-AI%20%E2%9C%A8-blueviolet.svg)](#the-story)

[Features](#-features) • [Demo](#-demo) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Comparison](#-comparison) • [Contributing](#-contributing)

---

<br>

**Kashat** is a comprehensive personal finance platform that gives you complete control over your financial data. Built entirely through AI-assisted development by a non-programmer, it proves that powerful software can be created by anyone with a vision.

<br>

[Get Started](#-quick-start) · [Report Bug](../../issues) · [Request Feature](../../issues)

</div>

---

## Table of Contents

- [The Story](#-the-story)
- [Why Kashat](#-why-kashat)
- [Features](#-features)
- [Demo](#-demo)
- [Comparison](#-comparison)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Architecture](#-architecture)
- [API Reference](#-api-reference)
- [Documentation](#-documentation)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Security](#-security)
- [Support](#-support)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 📖 The Story

> *"I couldn't write 'Hello World' six months ago."*

Kashat was built entirely through **"vibe coding"** — a revolutionary approach where the creator described their vision to AI assistants that generated production-ready code. With **zero programming knowledge**, a single individual built an enterprise-grade finance platform that rivals venture-backed competitors.

This isn't just an app. It's proof that the gatekeepers of software development are gone.

**What makes this remarkable:**
- 🧠 Every line of code was generated through AI conversation
- 🏗️ Production-ready architecture with FastAPI + Next.js
- 🔒 Enterprise-grade security (JWT, rate limiting, audit logs)
- 📊 Sophisticated ML-powered financial intelligence
- 🐳 Docker deployment ready from day one

---

## 🤔 Why Kashat

### The Problem

Traditional personal finance apps have a dirty secret: **you are the product**.

| App | What They Take |
|-----|----------------|
| Mint | Shut down. Sold your data to Credit Karma. |
| Rocket Money | Your data + $72-144/year + 35-60% of any savings |
| Albert | Your data + $120-480/year + cash advance fees |
| YNAB | $99/year for glorified spreadsheets |

### The Solution

**Kashat costs $0. Forever.** Your data never leaves your control.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Traditional Apps          vs          Kashat                  │
│                                                                 │
│   Your Data → Their Servers     Your Data → YOUR Server        │
│   They Profit from You          You Profit from Insights       │
│   Monthly Fees Forever          Free Forever                   │
│   Internet Required             Works Offline                   │
│   Locked In                     Export Anytime                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🤖 AI-Powered Intelligence

- **Smart Categorization** — ML auto-tags transactions with confidence scores
- **Merchant Recognition** — "AMZN*2847XK" → "Amazon"
- **Anomaly Detection** — Spots unusual spending patterns
- **Natural Language Insights** — Ask questions about your finances

</td>
<td width="50%" valign="top">

### 🔄 Automatic Detection

- **Transfer Matching** — Links inter-account transfers
- **Recurring Discovery** — Finds subscriptions automatically
- **Price Change Alerts** — Catches sneaky subscription increases
- **Income Detection** — Identifies salary and regular income

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📊 Powerful Analytics

- **Financial Health Score** — Comprehensive wellness metrics
- **Spending Trends** — Category breakdown over time
- **Cash Flow Analysis** — Income vs expenses visualization
- **Predictive Forecasting** — ML-powered budget projections
- **Merchant Rankings** — Top spending by vendor

</td>
<td width="50%" valign="top">

### 🔐 Privacy First

- **Self-Hosted** — Runs on YOUR infrastructure
- **Local AI** — LM Studio/Ollama for offline operation
- **No Tracking** — Zero analytics, zero telemetry
- **Full Export** — Your data in CSV/Parquet anytime
- **Open Source** — Audit every line of code

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📥 Flexible Import

- **CSV Upload** — Standard bank export format
- **PDF Parsing** — AI Vision extracts from statements
- **Multi-Bank** — Bank of America + more coming
- **Deduplication** — Smart duplicate prevention

</td>
<td width="50%" valign="top">

### ⚡ Modern Stack

- **Real-Time Updates** — WebSocket live sync
- **Sub-100ms API** — Blazing fast responses
- **Mobile Ready** — Responsive design
- **Dark Mode** — Easy on the eyes
- **Docker Deploy** — One command setup

</td>
</tr>
</table>

---

## 🎬 Demo

### Dashboard Overview
```
┌────────────────────────────────────────────────────────────────────────┐
│  KASHAT                                    [Search...]     [Settings]  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   $12,450    │  │   -$8,230    │  │   +$4,220    │  │    82%     │ │
│  │   Income     │  │   Spending   │  │   Net Flow   │  │   Health   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                        │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────┐ │
│  │  Spending by Category           │  │  Monthly Trend              │ │
│  │  ████████████ Food      32%     │  │       ╭───╮                 │ │
│  │  ████████     Housing   24%     │  │    ╭──╯   ╰──╮              │ │
│  │  ██████       Transport 18%     │  │ ───╯         ╰───           │ │
│  │  ████         Shopping  12%     │  │  J  F  M  A  M  J           │ │
│  └─────────────────────────────────┘  └─────────────────────────────┘ │
│                                                                        │
│  Recent Transactions                                                   │
│  ──────────────────────────────────────────────────────────────────── │
│  Today        Amazon Prime          Subscription     -$14.99    🔄    │
│  Today        Whole Foods           Groceries       -$127.43    ✓     │
│  Yesterday    Salary Deposit        Income        +$4,250.00    ✓     │
│  Yesterday    Transfer to Savings   Transfer        -$500.00    ↔     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Comparison

### Feature Comparison

| Feature | Kashat | Rocket Money | Albert | Mint† | YNAB |
|---------|:------:|:------------:|:------:|:----:|:----:|
| **Price** | **Free** | $6-12/mo | $10-40/mo | Dead | $14.99/mo |
| **Self-Hosted** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Local AI** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Works Offline** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Data Privacy** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **No Ads** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Full Data Export** | ✅ | Limited | Limited | N/A | ✅ |
| **AI Categorization** | ✅ | Basic | Basic | Basic | ❌ |
| **Transfer Detection** | ✅ | ❌ | ❌ | Basic | ❌ |
| **Recurring Detection** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **PDF Import** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Custom Rules** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **API Access** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Health Score** | ✅ | Premium | Premium | ❌ | ❌ |
| **Audit Trail** | ✅ | ❌ | ❌ | ❌ | ❌ |

*† Mint shut down January 2024*

### Annual Cost Comparison

```
                        Annual Cost
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │  Kashat        ▏ $0                                │
    │                                                     │
    │  YNAB          ████████████████▏ $180              │
    │                                                     │
    │  Rocket Money  ██████████████████████▏ $144        │
    │                                                     │
    │  Albert        ████████████████████████████████████│ $480
    │                                                     │
    └─────────────────────────────────────────────────────┘
                         $0   $100  $200  $300  $400  $500
```

**Switch to Kashat and save up to $480/year.**

---

## 🚀 Quick Start

### One-Line Install (Docker)

```bash
curl -fsSL https://raw.githubusercontent.com/Alexawy82/Floss/main/scripts/install.sh | bash
```

### Manual Quick Start

```bash
# Clone
git clone https://github.com/Alexawy82/Floss.git kashat && cd kashat

# Configure
cp .env.example .env

# Launch
docker compose up -d

# Open http://localhost:3000
```

**That's it.** You're running a privacy-first finance platform.

---

## 📦 Installation

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Docker** | 20.10+ | Latest |
| **Docker Compose** | 2.0+ | Latest |
| **RAM** | 1 GB | 2 GB+ |
| **Storage** | 500 MB | 2 GB+ |

<details>
<summary><b>Alternative: Manual Installation (without Docker)</b></summary>

#### Backend Setup

```bash
# Python 3.11+ required
cd apps/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment
export PYTHONPATH=apps/backend/src

# Run
uvicorn kashat.api.main:app --reload --port 8000
```

#### Frontend Setup

```bash
# Node.js 18+ required
cd apps/web

# Install dependencies
npm install

# Run
npm run dev
```

</details>

### Deployment Options

#### Option 1: Local Development

```bash
make dev          # Start all services
make dev-logs     # View logs
make dev-health   # Health check
make dev-down     # Stop all services
```

#### Option 2: Production (Docker Compose)

```bash
# Standard deployment
docker compose up -d

# With Traefik (SSL/reverse proxy)
docker compose -f docker-compose.corelab.yml up -d
```

#### Option 3: Raspberry Pi / Home Server

```bash
# Works on ARM64!
docker compose up -d
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/api/health

# Expected response:
# {"status": "healthy", "version": "2.0.0"}
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

#### Required Settings

```bash
# Security (REQUIRED - generate with: openssl rand -hex 32)
KASHAT_JWT_SECRET=your-super-secret-key-minimum-32-characters
```

#### AI Configuration

<table>
<tr>
<td width="33%">

**LM Studio (Recommended)**
```bash
KASHAT_AI_PROVIDER=lmstudio
KASHAT_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1
```
*100% local, 100% private*

</td>
<td width="33%">

**Ollama**
```bash
KASHAT_AI_PROVIDER=ollama
```
*Local alternative*

</td>
<td width="33%">

**OpenAI**
```bash
KASHAT_AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```
*Cloud-based*

</td>
</tr>
</table>

#### All Configuration Options

<details>
<summary><b>View Complete Configuration Reference</b></summary>

| Variable | Description | Default |
|----------|-------------|---------|
| **Core** |||
| `KASHAT_DATA_DIR` | Data storage directory | `~/.kashat` |
| `KASHAT_ENV` | Environment mode | `development` |
| `KASHAT_LOG_LEVEL` | Log verbosity | `INFO` |
| **Security** |||
| `KASHAT_JWT_SECRET` | JWT signing key | *required* |
| `KASHAT_ADMIN_TOKEN` | Admin API token | *optional* |
| `KASHAT_CORS` | Allowed origins | `localhost:3000` |
| `KASHAT_ALLOW_REGISTRATION` | Enable signup | `false` |
| **AI** |||
| `KASHAT_AI_PROVIDER` | AI backend | `lmstudio` |
| `KASHAT_AI_LMSTUDIO_BASE_URL` | LM Studio URL | `http://localhost:1234/v1` |
| `OPENAI_API_KEY` | OpenAI key | *optional* |
| `KASHAT_AI_MODEL_CATEGORIZE` | Categorization model | `qwen/qwen3-4b` |
| **Performance** |||
| `KASHAT_RATE_LIMIT` | API rate limit | `100/minute` |
| `KASHAT_DISABLE_REALTIME` | Disable WebSocket | `false` |
| **Docker** |||
| `BACKEND_PORT` | Backend port | `8000` |
| `WEB_PORT` | Frontend port | `3000` |

</details>

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              KASHAT                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         FRONTEND                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   Next.js   │  │  React 18   │  │     Tailwind CSS        │  │   │
│  │  │     14      │  │  + Hooks    │  │     + Radix UI          │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  TanStack   │  │  Recharts   │  │      WebSocket          │  │   │
│  │  │   Query     │  │   Charts    │  │     Real-time           │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          BACKEND                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   FastAPI   │  │    JWT      │  │     Rate Limiting       │  │   │
│  │  │   Python    │  │    Auth     │  │     + CORS              │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   SQLite    │  │  AI Engine  │  │     PDF Parser          │  │   │
│  │  │   Database  │  │  (Local/    │  │     (pdfplumber)        │  │   │
│  │  │             │  │   Cloud)    │  │                         │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                    ┌───────────────┼───────────────┐                   │
│                    ▼               ▼               ▼                   │
│              ┌──────────┐   ┌──────────┐   ┌──────────────┐            │
│              │ LM Studio│   │  Ollama  │   │   OpenAI     │            │
│              │  (Local) │   │  (Local) │   │   (Cloud)    │            │
│              └──────────┘   └──────────┘   └──────────────┘            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack Details

<table>
<tr>
<td width="50%">

#### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| Database | SQLite |
| Auth | JWT + bcrypt |
| AI | OpenAI / LM Studio / Ollama |
| PDF | pdfplumber |
| Validation | Pydantic |
| Testing | pytest |

</td>
<td width="50%">

#### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 |
| UI Library | React 18 |
| Components | Radix UI |
| Styling | Tailwind CSS |
| Data | TanStack Query |
| Tables | TanStack Table |
| Charts | Recharts |
| Testing | Playwright |

</td>
</tr>
</table>

### Data Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   CSV/   │────▶│  Parser  │────▶│   AI     │────▶│ Database │
│   PDF    │     │  Engine  │     │ Enricher │     │ (SQLite) │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                         │
                                                         ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   User   │◀────│    UI    │◀────│   API    │◀────│ Analytics│
│          │     │ (Next.js)│     │(FastAPI) │     │  Engine  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

---

## 📚 API Reference

### Authentication

```bash
# Login
POST /api/auth/login
Content-Type: application/json
{"username": "user", "password": "pass"}

# Response
{"access_token": "eyJ...", "token_type": "bearer"}
```

### Core Endpoints

<details>
<summary><b>Transactions</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transactions` | List transactions |
| `GET` | `/api/transactions/{id}` | Get single transaction |
| `POST` | `/api/transactions/{id}/category` | Set category |
| `PATCH` | `/api/transactions/{id}` | Update flags |
| `DELETE` | `/api/transactions/{id}` | Delete transaction |

**Query Parameters:**
- `start_date` — Filter start (YYYY-MM-DD)
- `end_date` — Filter end (YYYY-MM-DD)
- `category` — Filter by category
- `search` — Search description
- `limit` — Results per page (default: 50)
- `offset` — Pagination offset

</details>

<details>
<summary><b>Import/Export</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/imports/csv` | Import CSV file |
| `POST` | `/api/imports/pdf` | Import PDF statement |
| `GET` | `/api/export/transactions.csv` | Export as CSV |
| `POST` | `/api/export` | Export with options |

**CSV Import Example:**
```bash
curl -X POST http://localhost:8000/api/imports/csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@transactions.csv" \
  -F "account_id=checking"
```

</details>

<details>
<summary><b>Categories & Rules</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/categories` | List categories |
| `POST` | `/api/categories` | Create category |
| `PUT` | `/api/categories/{id}` | Update category |
| `DELETE` | `/api/categories/{id}` | Delete category |
| `GET` | `/api/rules` | List rules |
| `POST` | `/api/rules` | Create rule |
| `POST` | `/api/rules/{id}/apply` | Apply rule |
| `POST` | `/api/rules/preview` | Preview matches |

</details>

<details>
<summary><b>Transfers & Recurring</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transfers/suggest` | Detect transfers |
| `GET` | `/api/transfers` | List transfers |
| `POST` | `/api/transfers/confirm` | Confirm pair |
| `POST` | `/api/transfers/reject` | Reject pair |
| `POST` | `/api/recurring/suggest` | Detect recurring |
| `GET` | `/api/recurring` | List series |
| `POST` | `/api/recurring/confirm` | Confirm series |

</details>

<details>
<summary><b>Analytics</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analytics/monthly` | Monthly summary |
| `GET` | `/api/analytics/dashboard` | Dashboard data |
| `GET` | `/api/analytics/category-monthly` | By category |
| `GET` | `/api/analytics/merchants` | Top merchants |
| `GET` | `/api/analytics/cashflow` | Cash flow |
| `GET` | `/api/analytics/recurring` | Recurring analysis |
| `GET` | `/api/analytics/health` | Health score |

</details>

<details>
<summary><b>Admin</b></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/settings` | Get settings |
| `POST` | `/api/settings` | Update settings |
| `GET` | `/api/audit/logs` | Audit trail |
| `POST` | `/api/admin/backup` | Create backup |
| `POST` | `/api/admin/restore` | Restore backup |

</details>

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICKSTART.md) | Get running in 5 minutes |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment options |
| [API Reference](docs/API.md) | Complete API documentation |
| [Environment Config](.env.example) | All configuration options |

---

## 🗺️ Roadmap

### Version 2.1 (Next)
- [ ] Multi-currency support
- [ ] Investment tracking
- [ ] Goal setting & tracking
- [ ] Budget alerts

### Version 2.2
- [ ] Plaid integration (optional bank sync)
- [ ] Mobile app (React Native)
- [ ] Receipt scanning (OCR)
- [ ] Multi-user / family accounts

### Version 3.0
- [ ] Financial planning AI assistant
- [ ] Tax preparation exports
- [ ] Crypto tracking
- [ ] Open Banking API support

<details>
<summary><b>View Full Roadmap</b></summary>

See our [GitHub Projects board](../../projects) for the complete roadmap and current progress.

Have a feature request? [Open an issue](../../issues/new?template=feature_request.md)!

</details>

---

## 🤝 Contributing

We love contributions! Kashat was built by the community, for the community.

### Ways to Contribute

- 🐛 **Report Bugs** — [Open an issue](../../issues/new?template=bug_report.md)
- 💡 **Suggest Features** — [Request a feature](../../issues/new?template=feature_request.md)
- 📖 **Improve Docs** — Fix typos, add examples
- 🔧 **Submit PRs** — Bug fixes, features, improvements
- ⭐ **Star the Repo** — Help others discover Kashat

### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/Floss.git
cd Floss

# Create branch
git checkout -b feature/amazing-feature

# Make changes, then test
make test

# Commit (follow conventional commits)
git commit -m "feat: add amazing feature"

# Push and create PR
git push origin feature/amazing-feature
```

### Commit Convention

```
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting, no code change
refactor: code restructuring
test: adding tests
chore: maintenance
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🔒 Security

Security is paramount for a finance application.

### Security Features

- ✅ JWT authentication with secure tokens
- ✅ Password hashing with bcrypt
- ✅ Rate limiting to prevent abuse
- ✅ CORS protection
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention
- ✅ Audit logging for all changes
- ✅ No external data transmission (when using local AI)

### Reporting Vulnerabilities

**Please do not open public issues for security vulnerabilities.**

Email security concerns to: **[security email]**

See [SECURITY.md](SECURITY.md) for our security policy.

---

## 💬 Support

### Get Help

- 📖 [Documentation](docs/)
- 💬 [GitHub Discussions](../../discussions)
- 🐛 [Issue Tracker](../../issues)

### FAQ

<details>
<summary><b>Is my financial data safe?</b></summary>

Yes. Kashat runs entirely on your infrastructure. Your data never leaves your server. When using local AI (LM Studio/Ollama), even AI processing happens locally.

</details>

<details>
<summary><b>Can I use this without Docker?</b></summary>

Yes! See the manual installation section. You'll need Python 3.11+ and Node.js 18+.

</details>

<details>
<summary><b>What banks are supported for PDF import?</b></summary>

Currently Bank of America. More banks are being added. CSV import works with any bank that provides statement exports.

</details>

<details>
<summary><b>Is there a mobile app?</b></summary>

Not yet, but the web interface is fully responsive. A React Native app is on the roadmap.

</details>

<details>
<summary><b>Can multiple people use one instance?</b></summary>

Currently Kashat is designed for single-user use. Multi-user support is planned for v3.0.

</details>

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

```
MIT License

Copyright (c) 2024 Kashat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 🙏 Acknowledgments

### Built With AI

This entire application was created through **AI-assisted development** — proof that anyone with a vision can build professional software, regardless of programming background.

### Technologies

- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Next.js](https://nextjs.org/) — React framework
- [Radix UI](https://www.radix-ui.com/) — Accessible components
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
- [LM Studio](https://lmstudio.ai/) — Local AI models

### Inspiration

Built as a privacy-respecting alternative to commercial finance apps that monetize user data.

---

<div align="center">

### ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Alexawy82/Floss&type=Date)](https://star-history.com/#Alexawy82/Floss&Date)

---

**Kashat** — Your finances. Your data. Your control.

[⬆ Back to Top](#kashat)

</div>
