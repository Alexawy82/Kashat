# QUICK AUDIT PROMPT (Condensed Version)
## For AI tools with context limits

---

**Project**: LedgerLoop (Flos) - Personal Finance App  
**Location**: `C:\Users\Marwan\Desktop\AI\Flos`  
**Stack**: FastAPI + Next.js + DuckDB + OpenAI

---

## YOUR TASK

Perform a COMPLETE technical audit. Document EVERYTHING. Output to `docs/audit/`.

---

## WHAT TO DOCUMENT

### 1. STRUCTURE
- Directory tree with annotations
- Every file: path, purpose, LOC, key exports

### 2. BACKEND (apps/backend/src/ledgerloop/)
For each .py file:
- Purpose, classes, functions, dependencies
- What calls it, what it calls
- Database tables it touches
- AI involvement (prompts, models, fallbacks)

### 3. API (58 routers, 154 endpoints)
For each endpoint:
- Method, path, handler function
- Request/response schemas
- Database operations
- Example curl command

### 4. DATABASE (17 tables)
For each table:
- Columns with types
- Foreign keys
- Indexes
- Query patterns

### 5. AI LAYER (18 modules)
- Every prompt verbatim
- Every pattern dictionary (500+ patterns total)
- Model configs (temp, tokens, etc.)
- Fallback logic
- Categorization decision tree

### 6. FRONTEND (apps/web/src/)
- 15 pages: what they do, what APIs they call
- 50+ components: props, state, effects
- 14 hooks: what they fetch, caching strategy
- API client: openapi.json (8,836 lines)

### 7. DATA FLOWS (create Mermaid diagrams)
- Import: file → parse → normalize → dedupe → insert → AI enhance
- Categorization: rules → merchant memory → AI → pattern → fallback
- Transfer detection: v1/v2/v3 algorithms
- Recurring: normalization → grouping → cadence detection

### 8. ISSUES
- Duplicate/conflicting code
- Missing error handling
- Inconsistent patterns
- Security concerns
- Performance issues

### 9. RECOMMENDATIONS
- Critical (fix now)
- High (this week)
- Medium (this month)
- Low (backlog)

---

## OUTPUT FILES

```
docs/audit/
├── 00_EXECUTIVE_SUMMARY.md
├── 01_CODEBASE_STRUCTURE.md
├── 02_BACKEND_MODULES.md
├── 03_API_REFERENCE.md
├── 04_DATABASE_SCHEMA.md
├── 05_DATA_FLOWS.md
├── 06_AI_LAYER.md
├── 07_FRONTEND.md
├── 08_CONFIGURATION.md
├── 09_TESTING.md
├── 10_DEPENDENCIES.md
├── 11_TECHNICAL_DEBT.md
└── 12_RECOMMENDATIONS.md
```

---

## KEY FILES TO READ FIRST

```
# Backend core
apps/backend/src/ledgerloop/
├── api/main.py              # FastAPI app entry
├── db.py                    # Database connection
├── ingest_csv.py            # CSV import
├── ingest_pdf.py            # PDF import
├── normalization.py         # Text normalization
├── dedup.py                 # Deduplication
├── ai.py                    # Main AI service (1,497 lines)
├── ai_workflow.py           # Import workflow orchestration
├── ai_smart_categorization.py  # ML categorization (2,177 lines)
├── ai_enhanced_categorization.py  # Pattern categorization (1,346 lines)
├── transfers.py             # Transfer detection (3 versions)
├── recurring.py             # Recurring detection (1,628 lines)
├── rules.py                 # Rules engine

# Frontend core
apps/web/src/
├── app/                     # Next.js pages
├── components/              # React components
├── hooks/                   # Custom hooks (14 files)
├── lib/api/                 # API client
└── openapi.json             # Generated API spec

# Schema
docs/schema.sql              # Database schema (353 lines)
```

---

## KNOWN PROBLEM AREAS

1. **5 different categorization systems** that conflict
2. **3 different transfer detection algorithms** (v1, v2, v3)
3. **AI suggests categories that don't exist** in database
4. **Processing order is wrong** (detection runs after categorization)
5. **Pattern dictionaries are duplicated** across 3 files

---

## BE THOROUGH

- Read EVERY file
- Document EVERY function
- List EVERY pattern
- Capture EVERY prompt
- Note EVERY inconsistency
- Be brutally honest

START NOW.
