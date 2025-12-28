# LedgerLoop Cleanup & Audit Plan

## Current State: Unknown (Assumed Messy)
- Multiple AI modules that may overlap
- Unknown test coverage / pass rate
- Potential dead code
- Configuration drift
- Dependency bloat

---

## Phase 1: Health Check (Run First)

### 1.1 Can the backend even start?
```bash
cd C:\Users\Marwan\Desktop\AI\Flos
# Check if Python env works
.venv\Scripts\activate  # Windows
pip list > artifacts/current_deps.txt
python -c "from ledgerloop.api.main import app; print('Backend imports OK')"
```

### 1.2 Can the frontend build?
```bash
cd apps/web
npm install
npm run build 2>&1 | tee ../../artifacts/frontend_build.log
```

### 1.3 Do tests pass?
```bash
cd C:\Users\Marwan\Desktop\AI\Flos
pytest apps/backend/tests -v 2>&1 | tee artifacts/test_results.log
```

### 1.4 Database health
```bash
# Check if DB exists and has tables
python -c "
import duckdb
conn = duckdb.connect('.ledgerloop/ledgerloop.duckdb')
tables = conn.execute('SHOW TABLES').fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
    print(f'  {t[0]}: {count} rows')
"
```

---

## Phase 2: Code Inventory & Duplication Analysis

### 2.1 AI Module Audit
These 20+ AI files likely have massive overlap. Need to map:

| File | Purpose | Used By | Keep/Merge/Delete |
|------|---------|---------|-------------------|
| ai.py | Core service | ? | ? |
| ai_alerts.py | Notifications | ? | ? |
| ai_analytics.py | Insights | ? | ? |
| ai_automation.py | Auto workflows | ? | ? |
| ai_auto_categorization.py | Category assignment | ? | ? |
| ai_categories.py | Category matching | ? | ? |
| ai_category_acceptance.py | Accept suggestions | ? | ? |
| ai_data_quality.py | Validation | ? | ? |
| ai_dedup.py | Deduplication | ? | ? |
| ai_enhanced_categorization.py | Better categories | ? | ? |
| ai_forecasting.py | Predictions | ? | ? |
| ai_import.py | Import AI | ? | ? |
| ai_insights.py | Financial intel | ? | ? |
| ai_integration.py | Integration layer | ? | ? |
| ai_intelligent_dedup.py | Smarter dedup | ? | ? |
| ai_ml_features.py | ML engineering | ? | ? |
| ai_smart_categorization.py | Context categories | ? | ? |
| ai_smart_scheduling.py | Timing | ? | ? |
| ai_workflow.py | Multi-step | ? | ? |
| realtime_ai_analytics.py | Real-time AI | ? | ? |
| realtime_anomaly_detection.py | Anomaly | ? | ? |

### 2.2 Find actual imports
```bash
# Which AI modules are actually imported anywhere?
grep -r "from ledgerloop.ai" apps/backend/src --include="*.py" | grep -v __pycache__ > artifacts/ai_imports.txt
grep -r "import ledgerloop.ai" apps/backend/src --include="*.py" | grep -v __pycache__ >> artifacts/ai_imports.txt
```

### 2.3 Find dead files
```bash
# Files never imported by anything
# Run this Python script to find orphans
```

---

## Phase 3: What to Clean

### 3.1 Likely Duplicates to Merge
- `ai_dedup.py` + `ai_intelligent_dedup.py` → One dedup module
- `ai_categories.py` + `ai_auto_categorization.py` + `ai_smart_categorization.py` + `ai_enhanced_categorization.py` → One categorization module
- `ai_analytics.py` + `ai_insights.py` + `realtime_ai_analytics.py` → One analytics module

### 3.2 Root-level test files (should be in tests/)
These are scattered in root and should be consolidated:
- test_accept_all_categories.py
- test_ai_categorization_improvements.py
- test_ai_infrastructure.py
- test_ai_integration.py
- test_all_features.py
- test_category_management.py
- test_enhanced_classification.py
- test_integrated_workflow.py
- test_phase2_integration.py
- test_simple_accept_all.py

### 3.3 Artifacts folder
226+ log files in /logs - need rotation/cleanup
Multiple .testdata_cov* folders - delete all

### 3.4 Documentation consolidation
Multiple .md files that may be outdated:
- ACCEPT_ALL_IMPLEMENTATION_SUMMARY.md
- CATEGORY_MANAGEMENT_SOLUTION.md
- ENHANCED_CATEGORIZATION_SUMMARY.md
- FEATURE_ANALYSIS_2025.md
- GAPS.md
- PHASE_1_IMPLEMENTATION_GUIDE.md
- PLAN.md
- Plan_Status.md
- QA_REPORT.md
- RELEASE_NOTES.md
- SMART_4_PHASE_PLAN.md
- UI_COMPLETION_PLAN.md

→ Consolidate into: README.md, ARCHITECTURE.md, CHANGELOG.md, TODO.md

---

## Phase 4: Cleanup Actions

### 4.1 Delete dead code
```bash
# After confirming what's unused
rm -rf .testdata_cov*
rm -rf __pycache__ (all)
# Move old logs to archive or delete
```

### 4.2 Consolidate AI modules
Create clean structure:
```
ledgerloop/
  ai/
    __init__.py      # Public API
    core.py          # Base AI service
    categorization.py # All category AI
    dedup.py         # All dedup AI  
    analytics.py     # All analytics AI
    forecasting.py   # Predictions
    workflows.py     # Multi-step automation
```

### 4.3 Move tests
```bash
mv test_*.py apps/backend/tests/
```

### 4.4 Clean requirements
```bash
pip-compile requirements.in  # Regenerate locked deps
```

---

## Phase 5: Validation

### 5.1 Full test suite
```bash
pytest apps/backend/tests -v --tb=short
```

### 5.2 Frontend smoke test
```bash
cd apps/web && npm run build && npm run start
# Manual check: http://localhost:3000
```

### 5.3 Import a PDF
```bash
# Test the core workflow still works
curl -X POST http://localhost:8000/api/import/pdf -F "file=@bank/eStmt_2025-09-10.pdf"
```

---

## Execution Order for Claude Code

1. **FIRST**: Run Phase 1 health checks - find out what's broken
2. **SECOND**: Run Phase 2 inventory - map what exists and what's used
3. **THIRD**: Create backup branch: `git checkout -b pre-cleanup-backup`
4. **FOURTH**: Execute Phase 4 cleanup actions
5. **FIFTH**: Run Phase 5 validation
6. **SIXTH**: Update documentation

---

## Success Criteria

After cleanup:
- [ ] Backend starts without errors
- [ ] Frontend builds without errors
- [ ] All tests pass (or known failures documented)
- [ ] No duplicate AI modules
- [ ] No orphan files
- [ ] Clean folder structure
- [ ] Updated README reflects actual state
- [ ] < 10 files in root (excluding config)
