# Kashat Quick Start Guide

Get Kashat running in under 5 minutes with this step-by-step guide.

---

## Prerequisites

Before you begin, ensure you have:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Git | Any | `git --version` |

**System Requirements:**
- **RAM:** 1 GB minimum, 2 GB recommended
- **Storage:** 500 MB minimum, 2 GB recommended
- **OS:** Linux, macOS, or Windows with WSL2

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/Alexawy82/Floss.git kashat
cd kashat
```

---

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Generate a secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Update the JWT secret in .env (Linux/macOS)
sed -i.bak "s/KASHAT_JWT_SECRET=.*/KASHAT_JWT_SECRET=${JWT_SECRET}/" .env

# Or manually edit .env and set KASHAT_JWT_SECRET
```

**Important:** The `KASHAT_JWT_SECRET` must be at least 32 characters for security.

---

## Step 3: Launch Kashat

### Option A: Standard Docker Compose

```bash
# Build and start all services
docker compose up -d

# Check service status
docker compose ps
```

### Option B: Using Make (Development)

```bash
# Start development environment
make dev

# View logs
make dev-logs

# Check health
make dev-health
```

---

## Step 4: Verify Installation

### Check Backend Health

```bash
curl http://localhost:8000/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected"
}
```

### Access the Application

Open your browser and navigate to:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/api/health |

---

## Step 5: Import Your First Transactions

### Via Web Interface (Recommended)

1. Open http://localhost:3000
2. Click **"Import Data"** button
3. Select your bank statement (CSV or PDF)
4. Choose your account type
5. Review and confirm the import

### Via API

```bash
# Import a CSV file
curl -X POST http://localhost:8000/api/imports/csv \
  -F "file=@your-transactions.csv" \
  -F "account_id=checking"
```

---

## Supported Bank Formats

### CSV Import
Works with any bank that exports CSV. Common columns detected automatically:
- Date, Description, Amount
- Debit, Credit (separate columns)
- Balance, Category, Memo

### PDF Import (AI-Powered)
Currently supports:
- **Bank of America** statements
- More banks coming soon

---

## Next Steps

### Configure AI (Optional but Recommended)

Kashat supports three AI providers for intelligent categorization:

#### Local AI with LM Studio (Recommended - 100% Private)

1. Download [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Qwen 3 4B)
3. Start the local server on port 1234
4. Update `.env`:
   ```bash
   KASHAT_AI_PROVIDER=lmstudio
   KASHAT_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1
   ```

#### Local AI with Ollama

1. Install [Ollama](https://ollama.ai/)
2. Pull a model: `ollama pull qwen2:7b`
3. Update `.env`:
   ```bash
   KASHAT_AI_PROVIDER=ollama
   ```

#### Cloud AI with OpenAI

1. Get an API key from [OpenAI](https://platform.openai.com/)
2. Update `.env`:
   ```bash
   KASHAT_AI_PROVIDER=openai
   OPENAI_API_KEY=sk-your-api-key
   ```

### Explore Features

| Feature | Location | Description |
|---------|----------|-------------|
| **Dashboard** | `/` | Financial overview with charts |
| **Transactions** | `/transactions` | View and categorize transactions |
| **Transfers** | `/transfers` | Detect and link inter-account transfers |
| **Subscriptions** | `/subscriptions` | Track recurring payments |
| **Budget** | `/budget` | Set and monitor budgets |
| **Net Worth** | `/networth` | Track assets and liabilities |
| **Import** | `/import` | Import bank statements |
| **Settings** | `/settings` | Configure accounts and categories |

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Port Already in Use

```bash
# Change ports in .env
BACKEND_PORT=8001
WEB_PORT=3001

# Restart
docker compose down
docker compose up -d
```

### Database Issues

```bash
# Reset database (WARNING: deletes all data)
docker compose down -v
rm -rf /opt/kashat/data/*
docker compose up -d
```

### AI Not Working

1. Check AI provider is configured in `.env`
2. Verify the AI service is running:
   - LM Studio: Check the app is running with server started
   - Ollama: Run `ollama list` to verify models
   - OpenAI: Verify API key is valid

---

## Quick Commands Reference

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop all services |
| `docker compose logs -f` | Follow logs |
| `docker compose ps` | Check service status |
| `docker compose restart` | Restart all services |
| `make dev` | Start development environment |
| `make test` | Run test suite |
| `make smoke` | Run smoke tests |

---

## Getting Help

- **Documentation:** [docs/](../docs/)
- **Issues:** [GitHub Issues](https://github.com/Alexawy82/Floss/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Alexawy82/Floss/discussions)

---

**Congratulations!** You now have a fully functional, privacy-first personal finance platform running locally.

[Back to README](../README.md)
