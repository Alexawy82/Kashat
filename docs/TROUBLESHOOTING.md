# LedgerLoop Troubleshooting Guide

This guide covers common issues and their solutions.

## Table of Contents

1. [Startup Issues](#startup-issues)
2. [Login Problems](#login-problems)
3. [Import Issues](#import-issues)
4. [Database Issues](#database-issues)
5. [AI Features](#ai-features)
6. [Performance Issues](#performance-issues)
7. [Docker Issues](#docker-issues)
8. [Frontend Issues](#frontend-issues)

---

## Startup Issues

### Backend won't start

**Symptom:** `uvicorn: command not found` or module import errors

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH=apps/backend/src

# Try starting again
uvicorn ledgerloop.api.main:app --reload
```

### Port already in use

**Symptom:** `Address already in use` error

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000
# or on Windows
netstat -ano | findstr :8000

# Kill the process
kill <PID>
# or on Windows
taskkill /PID <PID> /F

# Or use a different port
uvicorn ledgerloop.api.main:app --port 8001
```

### Frontend won't start

**Symptom:** npm errors or build failures

**Solution:**
```bash
cd apps/web

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Next.js cache
rm -rf .next

# Try again
npm run dev
```

### Frontend starts but production server is wrong

**Symptom:** `next start` warns about `output: standalone`, missing chunks, or UI changes don’t appear

**Solution (production build):**
```bash
cd apps/web
npm run build
mkdir -p .next/standalone/.next
cp -R .next/static .next/standalone/.next/static
if [ -d public ]; then cp -R public .next/standalone/public; fi
node .next/standalone/server.js
```

---

## Authentication Notes

Authentication is currently disabled (single-user mode). If you deploy beyond localhost, treat all endpoints (including `/api/admin/*`) as publicly accessible and protect the host with network controls (localhost binding, firewall rules, SSH tunnel, or reverse proxy with auth).

---

## Import Issues

### CSV import fails

**Symptom:** "Invalid CSV format" or no transactions imported

**Causes and Solutions:**

1. **Wrong date format**
   - Ensure dates are in MM/DD/YYYY or YYYY-MM-DD format
   - Check for Excel date serial numbers

2. **Missing columns**
   - Required: date, description, amount
   - Optional: category, account

3. **Encoding issues**
   ```bash
   # Convert to UTF-8
   iconv -f ISO-8859-1 -t UTF-8 input.csv > output.csv
   ```

4. **Large file timeout**
   ```bash
   # Increase timeout for large imports
   curl --max-time 300 -F file=@large.csv http://localhost:8000/api/imports/csv
   ```

### PDF import fails

**Symptom:** "Failed to parse PDF" error

**Causes and Solutions:**

1. **Unsupported bank**
   - Currently only Bank of America PDFs are supported
   - Check file is a bank statement, not a bill

2. **Scanned PDF**
   - OCR PDFs are not supported
   - Use CSV export from your bank instead

3. **Password protected**
   - Remove PDF password first
   - Use your bank's unprotected export option

### Duplicate transactions

**Symptom:** Same transactions appear multiple times

**Solution:**
The deduplication algorithm checks date, amount, and description. If duplicates still appear:
```bash
# Run deduplication
curl -X POST http://localhost:8000/api/transactions/deduplicate

# Check for near-duplicates
curl "http://localhost:8000/api/transactions?description=MERCHANT"
```

---

## Database Issues

### Database locked

**Symptom:** `database is locked` error

**Solution:**
DuckDB only supports single-writer access:
```bash
# Stop all backend processes
pkill -f uvicorn
pkill -f gunicorn

# Check for remaining locks
lsof ~/.ledgerloop/ledgerloop.duckdb

# Restart backend
./start start backend
```

### Database corrupted

**Symptom:** "unable to open database file" or crash on startup

**Solution:**
```bash
# Try the self-healing restart
# Backend attempts this automatically on "invalidated database" errors

# If that fails, restore from backup
cp ~/.ledgerloop/backup_latest.duckdb ~/.ledgerloop/ledgerloop.duckdb

# Or start fresh (loses all data)
rm ~/.ledgerloop/ledgerloop.duckdb
./start start backend  # Creates new database
```

### Schema migration fails

**Symptom:** Migration error on startup

**Solution:**
```bash
# Check current schema version
sqlite3 ~/.ledgerloop/ledgerloop.duckdb "SELECT * FROM schema_version"

# Manually check migration files
ls apps/backend/db/migrations/

# If stuck, backup and recreate
cp ~/.ledgerloop/ledgerloop.duckdb ~/.ledgerloop/backup.duckdb
rm ~/.ledgerloop/ledgerloop.duckdb
./start start backend
```

---

## AI Features

### AI not responding

**Symptom:** AI categorization returns no results

**Solution:**
1. **Check AI provider is running:**
   ```bash
   # For LMStudio
   curl http://localhost:1234/v1/models

   # For OpenAI
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. **Check configuration:**
   ```bash
   # Verify AI settings
   curl http://localhost:8000/api/ai/ping \
     -H "Authorization: Bearer $TOKEN"
   ```

3. **Check logs for errors:**
   ```bash
   # Backend logs
   docker compose logs backend | grep -i ai
   ```

### LMStudio connection refused

**Symptom:** "Connection refused" to localhost:1234

**Solution:**
1. Ensure LMStudio is running
2. Check LMStudio server is enabled (Settings > Server)
3. Check the correct URL:
   ```bash
   export LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://localhost:1234/v1
   ```
4. For Docker, use host.docker.internal:
   ```bash
   LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
   ```

### AI responses are poor quality

**Symptom:** Wrong categories, low confidence

**Solution:**
1. Try a larger/better model
2. Adjust confidence threshold:
   ```bash
   curl -X POST "http://localhost:8000/api/ai/enhance/uncategorized" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"min_confidence": 0.7}'  # Increase threshold
   ```
3. Create more rules for common merchants (rules are faster and more accurate)

---

## Performance Issues

### Slow transaction loading

**Symptom:** Long wait times loading transactions

**Solution:**
1. **Add pagination:**
   ```bash
   # Use limit and offset
   curl "http://localhost:8000/api/transactions?limit=50&offset=0"
   ```

2. **Check database size:**
   ```bash
   ls -lh ~/.ledgerloop/ledgerloop.duckdb
   ```

3. **Optimize queries with indexes** (done automatically on startup)

### High memory usage

**Symptom:** Backend consuming too much RAM

**Solution:**
1. Reduce worker count:
   ```bash
   gunicorn ... --workers 1
   ```

2. Disable real-time features:
   ```bash
   export LEDGERLOOP_DISABLE_REALTIME=true
   ```

3. Use smaller AI models

### Frontend slow/laggy

**Symptom:** UI is unresponsive

**Solution:**
1. Reduce transaction display count
2. Disable animations in Settings
3. Clear browser cache
4. Check browser console for errors

---

## Docker Issues

### Container won't start

**Symptom:** Container exits immediately

**Solution:**
```bash
# Check logs
docker compose logs backend
docker compose logs web

# Check for missing env vars
docker compose config

# Recommended: bind to localhost (single-user mode; auth disabled)
echo "LL_BIND_IP=127.0.0.1" >> .env
```

### Volume permissions

**Symptom:** "Permission denied" accessing /data

**Solution:**
```bash
# Fix ownership
docker compose exec backend chown -R ledgerloop:ledgerloop /data

# Or recreate volume
docker compose down -v
docker compose up -d
```

### Can't connect to host services

**Symptom:** Container can't reach LMStudio on host

**Solution:**
Use `host.docker.internal`:
```yaml
environment:
  - LEDGERLOOP_AI_LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
```

On Linux, add to docker-compose.yml:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### Build fails

**Symptom:** Docker build errors

**Solution:**
```bash
# Clear Docker cache
docker builder prune -a

# Rebuild without cache
docker compose build --no-cache
```

---

## Frontend Issues

### Blank page / white screen

**Symptom:** Application doesn't load

**Solution:**
1. Check browser console (F12) for errors
2. Clear browser cache
3. Check API is reachable:
   ```bash
   curl http://localhost:8000/api/health
   ```
4. Verify NEXT_PUBLIC_API_BASE is correct

### API requests fail

**Symptom:** Network errors in console

**Solution:**
1. Check CORS settings match frontend URL
2. Verify API proxy in next.config.js
3. Check backend is running:
   ```bash
   curl http://localhost:8000/api/health
   ```

### Charts not rendering

**Symptom:** Analytics page shows no charts

**Solution:**
1. Check for JavaScript errors in console
2. Ensure data exists:
   ```bash
   curl http://localhost:8000/api/analytics/monthly \
     -H "Authorization: Bearer $TOKEN"
   ```
3. Try different date range

### Mobile layout broken

**Symptom:** UI elements overlap on mobile

**Solution:**
1. Clear browser cache
2. Force refresh (Ctrl+Shift+R)
3. Report issue with screenshot

---

## Getting More Help

### Collect Debug Information

```bash
# System info
echo "Node: $(node -v)"
echo "Python: $(python --version)"
echo "Docker: $(docker --version)"

# Service status
curl http://localhost:8000/api/health/detailed

# Recent logs
docker compose logs --tail=100 backend
docker compose logs --tail=100 web
```

### Log Locations

- **Docker:** `docker compose logs`
- **Bare metal:**
  - Backend: stdout or configured log file
  - Frontend: stdout
- **Application logs:** `~/.ledgerloop/logs/`

### Reporting Issues

When reporting issues, include:
1. Error message (exact text)
2. Steps to reproduce
3. Environment (OS, Docker version, etc.)
4. Relevant logs
5. Screenshots if UI issue

---

*LedgerLoop Troubleshooting Guide - v2.0*
