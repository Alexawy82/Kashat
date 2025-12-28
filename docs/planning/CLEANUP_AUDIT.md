# Dead Code Analysis - AI Modules

**Generated:** 2024-12-14

## Summary

| Metric | Count |
|--------|-------|
| Total AI modules | 19 |
| Active (used) | 13 |
| Dead code | 3 |
| Partial/Redundant | 3 |
| Total lines | 13,620 |
| Dead code lines | ~2,476 |

---

## AI Module Status Table

| File | Lines | Imported By | Used in Routes | Status |
|------|-------|-------------|----------------|--------|
| ai.py | 771 | ai_dedup, ai_auto_categorization, ai_workflow, ai_integration, ai_import, ai_categories, ai_enhanced_categorization, ai_analytics, realtime_ai_analytics, cli.py | routes/ai.py | **ACTIVE** |
| ai_alerts.py | 821 | realtime_integration, realtime_ai_analytics | - | **ACTIVE** |
| ai_analytics.py | 756 | ai_automation, ai_insights, ai_smart_scheduling, ai_alerts, ai_smart_categorization, realtime_ai_analytics, analytics/predictive_engine | routes/analytics.py | **ACTIVE** |
| ai_auto_categorization.py | 384 | - | routes/ai_categories.py | **ACTIVE** |
| ai_automation.py | 866 | - | - | **DEAD** |
| ai_categories.py | 435 | ai_workflow, ai_integration, ai_import, realtime_ai_analytics | routes/ai.py | **ACTIVE** |
| ai_category_acceptance.py | 530 | - | routes/ai_categories.py | **ACTIVE** |
| ai_data_quality.py | 986 | realtime_integration | - | **ACTIVE** |
| ai_dedup.py | 386 | ai_workflow | routes/ai.py | **ACTIVE** |
| ai_enhanced_categorization.py | 441 | ai_auto_categorization, ai_integration, ai_import, ai.py | routes/ai_categories.py, routes/ai_enhanced.py | **ACTIVE** |
| ai_forecasting.py | 773 | ai_smart_scheduling, ai_alerts, ai_insights, analytics/predictive_engine | routes/analytics.py | **ACTIVE** |
| ai_import.py | 335 | ai_workflow | routes/imports.py | **ACTIVE** |
| ai_insights.py | 775 | ai_automation, ai_alerts, realtime_ai_analytics | - | **ACTIVE** |
| ai_integration.py | 529 | - | routes/ai.py | **ACTIVE** |
| ai_intelligent_dedup.py | 948 | realtime_integration, realtime_ai_analytics | - | **PARTIAL** (overlaps with ai_dedup.py) |
| ai_ml_features.py | 587 | - | - | **DEAD** |
| ai_smart_categorization.py | 1,816 | ai_category_acceptance, ai_auto_categorization, ai_data_quality, ai_integration, ai_import, realtime_integration, realtime_ai_analytics, test_merchant_memory.py | routes/transactions.py, routes/ai.py, routes/ai_categories.py, routes/ai_enhanced.py, routes/categories.py | **ACTIVE** |
| ai_smart_scheduling.py | 1,023 | - | - | **DEAD** |
| ai_workflow.py | 458 | - | routes/imports.py | **ACTIVE** |

---

## Dead Code Analysis

### Completely Dead (3 modules, ~2,476 lines)

#### 1. `ai_automation.py` (866 lines) - **DEAD**
- **Purpose:** AI-powered automation for rules, recurring transactions, alerts, data quality
- **Why dead:** Never imported anywhere in the codebase
- **Overlaps with:**
  - `ai_alerts.py` (alerts)
  - `ai_insights.py` (insights)
  - `ai_smart_scheduling.py` (scheduling)
- **Recommendation:** DELETE or merge relevant parts into active modules

#### 2. `ai_ml_features.py` (587 lines) - **DEAD**
- **Purpose:** ML feature extraction for transactions (text, amount, temporal features)
- **Why dead:** Never imported anywhere in the codebase
- **Overlaps with:** `ai_smart_categorization.py` (has its own feature extraction)
- **Recommendation:** DELETE - the features are too ML-heavy without an actual ML model

#### 3. `ai_smart_scheduling.py` (1,023 lines) - **DEAD**
- **Purpose:** Smart scheduling for recurring transactions
- **Why dead:** Never imported anywhere in the codebase
- **Overlaps with:** `recurring.py` (the actual recurring detection module)
- **Recommendation:** DELETE - functionality exists in recurring.py

---

## Duplicate/Overlapping Responsibilities

### 1. Deduplication (ai_dedup.py vs ai_intelligent_dedup.py)

| Module | Lines | Class | Used By |
|--------|-------|-------|---------|
| ai_dedup.py | 386 | AIDeduplicator | ai_workflow.py, routes/ai.py |
| ai_intelligent_dedup.py | 948 | IntelligentDuplicateDetector | realtime_integration.py, realtime_ai_analytics.py |

**Issue:** Both have `DuplicateCandidate` dataclass. Two separate dedup systems:
- `ai_dedup.py` - Basic dedup, used in batch workflows
- `ai_intelligent_dedup.py` - Advanced realtime dedup

**Recommendation:** Keep both but consolidate shared code. ai_intelligent_dedup.py should import from ai_dedup.py.

### 2. Categorization (multiple overlapping modules)

| Module | Purpose | Lines |
|--------|---------|-------|
| ai.py | Base AI service, CategorySuggestion | 771 |
| ai_categories.py | SmartCategorySuggestion, category matching | 435 |
| ai_enhanced_categorization.py | Enhanced categorization with merchant patterns | 441 |
| ai_smart_categorization.py | Merchant memory, learning from user categorizations | 1,816 |
| ai_auto_categorization.py | Batch auto-categorization | 384 |
| ai_category_acceptance.py | Accept/reject AI suggestions | 530 |

**Issue:** 6 modules all doing categorization with overlapping responsibilities.

**Recommendation:** Consolidate into 2-3 modules:
1. `ai_categorization.py` - Core categorization logic
2. `ai_merchant_memory.py` - Merchant learning
3. `ai_category_api.py` - API helpers for accept/reject

### 3. Analytics/Insights (overlapping modules)

| Module | Purpose | Lines |
|--------|---------|-------|
| ai_analytics.py | Spending analysis, trends | 756 |
| ai_insights.py | High-level financial insights | 775 |
| ai_forecasting.py | Future predictions | 773 |

**Issue:** All three analyze spending patterns with some overlap.

**Recommendation:** Keep separate - they have distinct purposes and are all actively used.

---

## Recommendations

### Immediate Actions (Safe to Delete)

1. **DELETE `ai_automation.py`** (866 lines)
   - No imports, no routes
   - Functionality duplicated elsewhere

2. **DELETE `ai_ml_features.py`** (587 lines)
   - No imports, no routes
   - Unused ML features

3. **DELETE `ai_smart_scheduling.py`** (1,023 lines)
   - No imports, no routes
   - `recurring.py` handles this

### Future Consolidation

1. **Merge dedup modules:**
   - Keep `ai_intelligent_dedup.py` as primary
   - Have it extend/import from simplified `ai_dedup.py`

2. **Consolidate categorization:**
   - Current: 6 modules (~4,377 lines)
   - Target: 2-3 modules (~2,000 lines)

---

## Code Statistics

```
Total AI module lines:     13,620
Dead code lines:            2,476 (18%)
After cleanup:             11,144

Active modules:                13
After consolidation:           10 (target)
```

---

## Files to Delete (Safe)

```bash
rm apps/backend/src/ledgerloop/ai_automation.py
rm apps/backend/src/ledgerloop/ai_ml_features.py
rm apps/backend/src/ledgerloop/ai_smart_scheduling.py
```

Also update `.coveragerc` to remove these from coverage exclusions.

---

## API Consistency Audit

**Generated:** 2024-12-14

### Summary

| Metric | Count |
|--------|-------|
| Total backend routes | 134 |
| Used by frontend | 73 |
| Zombie (unused) | 57 |
| Missing (frontend expects) | 4 |

---

### All Backend Routes (by module)

#### /api/health (1 route)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/health | status/page.tsx |

#### /api/accounts (1 route)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/accounts | data-management/page.tsx |

#### /api/transactions (8 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/transactions | EnhancedTransactions.tsx, AppDataContext.tsx |
| GET | /api/transactions/stats | - |
| GET | /api/transactions/{tx_id} | - |
| PATCH | /api/transactions/{tx_id} | AppDataContext.tsx |
| POST | /api/transactions/{tx_id}/category | EnhancedTransactions.tsx |
| DELETE | /api/transactions/{tx_id} | - |
| GET | /api/transactions/{tx_id}/ai-details | - |
| POST | /api/transactions/batch | transfers/page.tsx |

#### /api/categories (5 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/categories | categories/page.tsx, rules/page.tsx, AICategoryMappingPanel.tsx |
| POST | /api/categories | categories/page.tsx, EnhancedTransactions.tsx |
| GET | /api/categories/{category_id}/usage | - |
| DELETE | /api/categories/{category_id} | - |
| POST | /api/categories/merge | categories/page.tsx |

#### /api/rules (7 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/rules | rules/page.tsx |
| POST | /api/rules | rules/page.tsx, ingest/page.tsx |
| GET | /api/rules/export | - |
| POST | /api/rules/import | rules/page.tsx |
| POST | /api/rules/preview | rules/page.tsx |
| POST | /api/rules/{rule_id}/apply | rules/page.tsx |
| GET | /api/rules/suggestions | - |

#### /api/transfers (7 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/transfers/suggest | - |
| GET | /api/transfers | transfers/page.tsx |
| POST | /api/transfers/group/{group_id}/analytics | transfers/page.tsx |
| POST | /api/transfers/confirm | transfers/page.tsx |
| POST | /api/transfers/reject | transfers/page.tsx |
| POST | /api/transfers/suggest_v2 | transfers/page.tsx |

#### /api/recurring (5 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/recurring/suggest | recurring/page.tsx |
| GET | /api/recurring | recurring/page.tsx |
| POST | /api/recurring/confirm | recurring/page.tsx |
| POST | /api/recurring/reject | recurring/page.tsx |
| GET | /api/recurring/{series_id}/transactions | recurring/page.tsx |

#### /api/analytics (21 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/analytics/monthly | SharedAnalyticsService.ts |
| GET | /api/analytics/category-monthly | SharedAnalyticsService.ts |
| GET | /api/analytics/merchants | SharedAnalyticsService.ts |
| GET | /api/analytics/cashflow | SharedAnalyticsService.ts |
| GET | /api/analytics/summary | - |
| GET | /api/analytics/recurring | - |
| GET | /api/analytics/ai/spending-patterns | SharedAnalyticsService.ts |
| GET | /api/analytics/predictions | SharedAnalyticsService.ts |
| GET | /api/analytics/ai/trends | SharedAnalyticsService.ts |
| GET | /api/analytics/ai/anomalies | - |
| GET | /api/analytics/ai/forecasts/spending | - |
| GET | /api/analytics/ai/forecasts/income | - |
| GET | /api/analytics/ai/forecasts/cashflow | - |
| GET | /api/analytics/ai/predictions/category/{name} | - |
| POST | /api/analytics/ai/comprehensive-insights | - |
| GET | /api/analytics/ai/dashboard-summary | SharedAnalyticsService.ts |
| GET | /api/analytics/dashboard | AppDataContext.tsx |
| GET | /api/analytics/predictive/patterns | SpendingPatterns.tsx |
| GET | /api/analytics/predictive/cashflow-forecast | CashFlowForecast.tsx |
| GET | /api/analytics/predictive/insights | PredictiveInsights.tsx |

#### /api/import (12 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/import/runs | data-management/page.tsx |
| GET | /api/import/runs/{run_id}/files | data-management/page.tsx |
| GET | /api/import/runs/{run_id}/summary | data-management/page.tsx |
| DELETE | /api/import/runs/{run_id} | data-management/page.tsx |
| POST | /api/import/runs/{run_id}/reprocess | data-management/page.tsx |
| POST | /api/import/bulk | data-management/page.tsx |
| POST | /api/import/csv | ingest/page.tsx |
| POST | /api/import/pdf | ingest/page.tsx |
| GET | /api/import/report/{run_id} | - |
| GET | /api/import/{run_id}/ai-analysis | ingest/page.tsx |
| POST | /api/import/suggest-rules | ingest/page.tsx |
| POST | /api/import/backfill-hashes | - |

#### /api/export (3 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/export/transactions.csv | - |
| GET | /api/export/csv | - |
| POST | /api/export | - |

#### /api/detect (5 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/detect/zelle | data-management/page.tsx |
| POST | /api/detect/zelle/run | - |
| POST | /api/detect/auto | - |
| POST | /api/detect/income | data-management/page.tsx |
| POST | /api/detect/adjustments | data-management/page.tsx |

#### /api/settings (2 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/settings | - |
| POST | /api/settings | - |

#### /api/admin (14 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/admin/data/stats | settings/page.tsx |
| POST | /api/admin/data/optimize | settings/page.tsx |
| POST | /api/admin/data/delete-transactions | settings/page.tsx |
| POST | /api/admin/data/reset-ai | settings/page.tsx |
| POST | /api/admin/data/delete-all | settings/page.tsx |
| POST | /api/admin/data/backup | settings/page.tsx |
| GET | /api/admin/data/backup/{name} | - |
| POST | /api/admin/data/restore | settings/page.tsx |
| GET | /api/admin/ai-mapping | AICategoryMappingPanel.tsx |
| POST | /api/admin/ai-mapping | AICategoryMappingPanel.tsx |
| DELETE | /api/admin/ai-mapping | - |
| POST | /api/admin/data/factory-reset | settings/page.tsx |
| POST | /api/admin/data/wipe-all | settings/page.tsx |

#### /api/audit (2 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/audit/logs | audit/page.tsx, export/page.tsx |
| POST | /api/audit/client | Telemetry.ts |

#### /api/ai (35 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/ai/analyze/transaction/{id} | AppDataContext.tsx |
| POST | /api/ai/analyze/bulk | SharedAnalyticsService.ts |
| POST | /api/ai/normalize/merchant | - |
| GET | /api/ai/suggestions/categories/{id} | - |
| GET | /api/ai/stats | - |
| GET | /api/ai/suggestions/smart-categories/{id} | - |
| POST | /api/ai/categories/auto-create | EnhancedTransactions.tsx |
| POST | /api/ai/suggestions/apply-smart-category | EnhancedTransactions.tsx |
| GET | /api/ai/categories/usage-stats | - |
| POST | /api/ai/enhance/uncategorized | EnhancedTransactions.tsx, ai/page.tsx |
| GET | /api/ai/bulk-job/{job_id} | EnhancedTransactions.tsx, ai/page.tsx |
| POST | /api/ai/bulk-job/{job_id}/cancel | ai/page.tsx |
| POST | /api/ai/bulk-job/{job_id}/retry | ai/page.tsx |
| GET | /api/ai/bulk-jobs | ai/page.tsx |
| GET | /api/ai/duplicates/detect | - |
| POST | /api/ai/duplicates/merge | - |
| GET | /api/ai/duplicates/stats | - |
| GET | /api/ai/ping | settings/page.tsx |
| POST | /api/ai/reset | - |
| POST | /api/ai/process/integrated | - |
| POST | /api/ai/process/transaction/{id} | - |
| POST | /api/ai/workflow/full-detection | - |
| GET | /api/ai/detection/summary | - |
| POST | /api/ai/detection/update-markers | - |
| GET | /api/ai/categories/gap-analysis | - |
| POST | /api/ai/categories/bootstrap | - |
| POST | /api/ai/categories/process-suggestion | - |
| GET | /api/ai/categories/pending-suggestions | - |
| POST | /api/ai/categories/approve-suggestion | - |
| POST | /api/ai/categories/bulk-fix | - |
| GET | /api/ai/categories/success-metrics | - |
| POST | /api/ai/merchant-memory/learn | - |
| GET | /api/ai/merchant-memory/stats | EnhancedDashboard.tsx |
| POST | /api/ai/merchant-memory/extract | - |
| GET | /api/ai/merchant-memory/learned-mappings | - |
| DELETE | /api/ai/merchant-memory/mapping | - |
| POST | /api/ai/merchant-memory/clear-all | - |

#### /api/ai-categories (9 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/ai-categories/accept-single | - |
| POST | /api/ai-categories/accept-batch | EnhancedTransactions.tsx |
| GET | /api/ai-categories/metrics | ai/page.tsx |
| POST | /api/ai-categories/backfill-provider-mappings | ai/page.tsx |
| POST | /api/ai-categories/preview-batch | EnhancedTransactions.tsx |
| POST | /api/ai-categories/categorize-transactions | - |
| GET | /api/ai-categories/suggestions-status/{id} | - |
| POST | /api/ai-categories/auto-categorize-uncategorized | - |
| GET | /api/ai-categories/category-coverage | - |

#### /api/ai-enhanced (5 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| POST | /api/ai-enhanced/enhance-transactions | - |
| GET | /api/ai-enhanced/reenhance-all | - |
| POST | /api/ai-enhanced/fix-purchase-categories | - |
| GET | /api/ai-enhanced/test-enhanced/{id} | - |
| GET | /api/ai-enhanced/enhancement-stats | - |

#### /api/realtime (8 routes)
| Method | Route | Frontend Uses |
|--------|-------|---------------|
| GET | /api/realtime/status | - |
| GET | /api/realtime/health/{account_id} | RealTimeDashboard.tsx |
| GET | /api/realtime/metrics/{account_id} | - |
| POST | /api/realtime/test-event | - |
| GET | /api/realtime/recent-events/{account_id} | - |
| POST | /api/realtime/simulate-transaction | RealTimeDashboard.tsx |
| GET | /api/realtime/analytics/{account_id}/live | RealTimeDashboard.tsx |
| POST | /api/realtime/alerts/test | RealTimeDashboard.tsx |

---

### ZOMBIE ROUTES (Backend exists, Frontend never calls)

| Route | Category | Recommendation |
|-------|----------|----------------|
| GET /api/transactions/stats | transactions | KEEP - useful stats endpoint |
| GET /api/transactions/{tx_id} | transactions | KEEP - single transaction lookup |
| DELETE /api/transactions/{tx_id} | transactions | KEEP - delete functionality |
| GET /api/transactions/{tx_id}/ai-details | transactions | KEEP - AI details |
| GET /api/categories/{category_id}/usage | categories | KEEP - category stats |
| DELETE /api/categories/{category_id} | categories | KEEP - delete functionality |
| GET /api/rules/export | rules | KEEP - export rules JSON |
| GET /api/rules/suggestions | rules | KEEP - rule suggestions |
| POST /api/transfers/suggest | transfers | DELETE - replaced by suggest_v2 |
| GET /api/analytics/summary | analytics | KEEP - summary endpoint |
| GET /api/analytics/recurring | analytics | KEEP - recurring analytics |
| GET /api/analytics/ai/anomalies | analytics | KEEP - anomaly detection |
| GET /api/analytics/ai/forecasts/* | analytics | KEEP - forecasting (4 routes) |
| POST /api/analytics/ai/comprehensive-insights | analytics | KEEP - comprehensive insights |
| GET /api/import/report/{run_id} | import | KEEP - import report |
| POST /api/import/backfill-hashes | import | KEEP - admin utility |
| POST /api/detect/zelle/run | detect | DELETE - duplicate of /zelle |
| POST /api/detect/auto | detect | KEEP - auto detection |
| GET /api/export/* | export | KEEP - export functionality (3 routes) |
| GET/POST /api/settings | settings | KEEP - settings management |
| GET /api/admin/data/backup/{name} | admin | KEEP - download backup |
| DELETE /api/admin/ai-mapping | admin | KEEP - delete mapping |
| POST /api/ai/normalize/merchant | ai | KEEP - merchant normalization |
| GET /api/ai/suggestions/* | ai | KEEP - suggestions endpoints |
| GET /api/ai/stats | ai | KEEP - AI stats |
| GET /api/ai/categories/* | ai | KEEP - category management |
| GET /api/ai/duplicates/* | ai | KEEP - dedup endpoints |
| POST /api/ai/reset | ai | KEEP - reset AI service |
| POST /api/ai/process/* | ai | KEEP - processing endpoints |
| POST /api/ai/workflow/* | ai | KEEP - workflow endpoints |
| GET /api/ai/detection/summary | ai | KEEP - detection summary |
| POST /api/ai/detection/update-markers | ai | KEEP - marker updates |
| POST /api/ai/merchant-memory/* | ai | KEEP - merchant memory |
| POST /api/ai-categories/accept-single | ai-categories | KEEP - single accept |
| POST /api/ai-categories/categorize-transactions | ai-categories | KEEP - batch categorize |
| GET /api/ai-categories/suggestions-status/{id} | ai-categories | KEEP - suggestion status |
| POST /api/ai-categories/auto-categorize-uncategorized | ai-categories | KEEP - auto categorize |
| GET /api/ai-categories/category-coverage | ai-categories | KEEP - coverage stats |
| POST /api/ai-enhanced/* | ai-enhanced | KEEP - enhancement endpoints |
| GET /api/realtime/status | realtime | KEEP - status endpoint |
| GET /api/realtime/metrics/{account_id} | realtime | KEEP - metrics |
| POST /api/realtime/test-event | realtime | KEEP - testing |
| GET /api/realtime/recent-events/{account_id} | realtime | KEEP - event history |

**Routes Safe to Delete (2):**
1. `POST /api/transfers/suggest` - Replaced by suggest_v2
2. `POST /api/detect/zelle/run` - Duplicate of /zelle

---

### MISSING ROUTES (Frontend expects but Backend doesn't have)

| Expected Route | Frontend File | Status |
|----------------|---------------|--------|
| POST /api/transactions/import | WorkflowIntegrationExamples.tsx | EXAMPLE FILE - not real usage |
| GET /api/accounts/{id}/reconcile | WorkflowIntegrationExamples.tsx | EXAMPLE FILE - not real usage |
| POST /api/budget/analyze | WorkflowIntegrationExamples.tsx | EXAMPLE FILE - not real usage |
| POST /api/expenses/categorize | WorkflowIntegrationExamples.tsx | EXAMPLE FILE - not real usage |
| POST /api/ai/suggestions/opt-out | EnhancedTransactions.tsx | **MISSING** - needs backend route |

**Action Required:**
- Add `POST /api/ai/suggestions/opt-out` endpoint to routes/ai.py

---

### Route Totals by Module

| Module | Routes | Frontend Uses | Usage % |
|--------|--------|---------------|---------|
| health | 1 | 1 | 100% |
| accounts | 1 | 1 | 100% |
| transactions | 8 | 4 | 50% |
| categories | 5 | 3 | 60% |
| rules | 7 | 5 | 71% |
| transfers | 6 | 5 | 83% |
| recurring | 5 | 5 | 100% |
| analytics | 21 | 10 | 48% |
| import | 12 | 8 | 67% |
| export | 3 | 0 | 0% |
| detect | 5 | 3 | 60% |
| settings | 2 | 0 | 0% |
| admin | 14 | 10 | 71% |
| audit | 2 | 2 | 100% |
| ai | 37 | 11 | 30% |
| ai-categories | 9 | 4 | 44% |
| ai-enhanced | 5 | 0 | 0% |
| realtime | 8 | 4 | 50% |
| **TOTAL** | **134** | **73** | **54%** |

---

### Recommendations

#### Immediate Actions
1. **Add missing route:** `POST /api/ai/suggestions/opt-out`
2. **Delete unused routes:**
   - `POST /api/transfers/suggest` (replaced by suggest_v2)
   - `POST /api/detect/zelle/run` (duplicate)

#### Low Priority Cleanup
- Export routes (0% used) - Keep for future use
- Settings routes (0% used) - Keep for configuration
- AI-enhanced routes (0% used) - Consider if feature is needed

#### Module Health
- **Healthy (>70% usage):** health, accounts, rules, transfers, recurring, admin, audit
- **Moderate (40-70%):** transactions, categories, import, detect, analytics, realtime, ai-categories
- **Low (<40%):** export, settings, ai, ai-enhanced

---

## Frontend Health

**Generated:** 2024-12-14

### Build Status

| Metric | Result |
|--------|--------|
| Build | **SUCCESS** |
| TypeScript errors | 0 |
| Warnings | 1 (baseline-browser-mapping outdated) |
| Pages compiled | 18 |
| npm packages | 188 |
| Vulnerabilities | 2 (1 high, 1 critical) |

### Pages Built

| Route | Size | First Load JS | Type |
|-------|------|---------------|------|
| / | 12.7 kB | 107 kB | Dynamic |
| /ai | 3.31 kB | 90.4 kB | Static |
| /audit | 3.7 kB | 90.7 kB | Static |
| /categories | 3.57 kB | 90.6 kB | Static |
| /export | 3.36 kB | 90.4 kB | Static |
| /ingest | 2.97 kB | 93.4 kB | Static |
| /live | 4.61 kB | 91.7 kB | Static |
| /metrics | 2 kB | 89 kB | Static |
| /recurring | 3.94 kB | 91 kB | Static |
| /rules | 3.77 kB | 90.8 kB | Static |
| /settings | 8.12 kB | 98.6 kB | Static |
| /settings/data-management | 4.08 kB | 91.1 kB | Static |
| /status | 3.85 kB | 90.9 kB | Static |
| /transactions | 13.8 kB | 108 kB | Static |
| /transfers | 4 kB | 91 kB | Static |

### Security Vulnerabilities

| Package | Severity | Issue | Fix |
|---------|----------|-------|-----|
| next@14.2.3 | **CRITICAL** | Multiple vulnerabilities (Cache poisoning, DoS, SSRF, Auth bypass) | Update to 14.2.35+ |
| glob@10.2.0-10.4.5 | HIGH | Command injection via -c/--cmd | `npm audit fix` |

**Action Required:**
```bash
npm audit fix --force  # Updates next to 14.2.35
```

---

### Components Analysis

#### All Components (26 files)

| Component | Location | Imported By | Status |
|-----------|----------|-------------|--------|
| EnhancedDashboard | dashboard/ | app/page.tsx | **ACTIVE** |
| EnhancedTransactions | transactions/ | app/transactions/page.tsx | **ACTIVE** |
| SharedFilters | filters/ | app/page.tsx, app/transactions/page.tsx | **ACTIVE** |
| RealTimeDashboard | / | app/live/page.tsx | **ACTIVE** |
| LoadingSpinner | / | app/settings/page.tsx | **ACTIVE** |
| ErrorDisplay | / | app/settings/page.tsx | **ACTIVE** |
| SpendingPatterns | analytics/ | EnhancedDashboard.tsx | **ACTIVE** |
| CashFlowForecast | analytics/ | EnhancedDashboard.tsx | **ACTIVE** |
| PredictiveInsights | analytics/ | EnhancedDashboard.tsx | **ACTIVE** |
| ProgressTracker (workflow) | workflow/ | WorkflowDashboard.tsx, ImportWizard.tsx, WorkflowIntegrationExamples.tsx | **ACTIVE** |
| ProgressTracker (import) | import/ | BatchImportManager.tsx | **ACTIVE** |
| NotificationSystem | workflow/ | WorkflowProvider.tsx | **ACTIVE** |
| WorkflowDashboard | workflow/ | - | **ORPHAN** (only internal imports) |
| RuleBuilder | automation/ | AutomationEngine.ts, BulkActionProcessor.ts | **ACTIVE** |
| ui/index | ui/ | ApprovalFlow.tsx, ReviewWizard.tsx | **ACTIVE** |
| ActionCenter | dashboard/ | - | **ORPHAN** |
| AIInsightsWidget | shared/ | - | **ORPHAN** |
| BatchImportManager | import/ | - | **ORPHAN** |
| ImportWizard | import/ | - | **ORPHAN** |
| LazyLoading | performance/ | - | **ORPHAN** |
| ReviewWizard | review/ | - | **ORPHAN** |
| ApprovalFlow | approval/ | - | **ORPHAN** |
| SwipeableList | mobile/ | - | **ORPHAN** |
| MobileNavigation | mobile/ | - | **ORPHAN** |
| HelpSystem | help/ | - | **ORPHAN** |
| SharedFilters.test | filters/ | - | TEST FILE |

---

### Dead/Orphan Components (10)

These components are defined but never imported in the application:

| Component | Lines | Purpose | Recommendation |
|-----------|-------|---------|----------------|
| ActionCenter | ~200 | Dashboard action items | INTEGRATE or DELETE |
| AIInsightsWidget | ~100 | AI insights display | INTEGRATE or DELETE |
| BatchImportManager | ~300 | Bulk import UI | INTEGRATE or DELETE |
| ImportWizard | ~200 | Import wizard flow | INTEGRATE or DELETE |
| LazyLoading | ~530 | Performance HOC | INTEGRATE or DELETE |
| ReviewWizard | ~500 | Review workflow | INTEGRATE or DELETE |
| ApprovalFlow | ~570 | Approval workflow | INTEGRATE or DELETE |
| SwipeableList | ~480 | Mobile swipe UI | INTEGRATE or DELETE |
| MobileNavigation | ~430 | Mobile nav component | INTEGRATE or DELETE |
| HelpSystem | ~400 | Help/docs system | INTEGRATE or DELETE |
| WorkflowDashboard | ~200 | Workflow overview | INTEGRATE or DELETE |

**Total orphan code: ~3,910 lines**

These components appear to be:
1. **Planned features** - Built but not yet integrated
2. **Mobile-first components** - SwipeableList, MobileNavigation
3. **Workflow components** - ApprovalFlow, ReviewWizard, WorkflowDashboard

**Recommendation:** Review each component. Either:
- Integrate into the app (add imports/routes)
- Move to `archive/` folder for future use
- Delete if no longer needed

---

### Page Routing Analysis

All 15 pages are properly routed via Next.js App Router:

| Page | Route | Uses Components |
|------|-------|-----------------|
| Dashboard | / | EnhancedDashboard, SharedFilters |
| Transactions | /transactions | EnhancedTransactions, SharedFilters |
| Live | /live | RealTimeDashboard |
| Settings | /settings | LoadingSpinner, ErrorDisplay |
| Data Management | /settings/data-management | - |
| Categories | /categories | - |
| Rules | /rules | - |
| Transfers | /transfers | - |
| Recurring | /recurring | - |
| AI | /ai | - |
| Audit | /audit | - |
| Export | /export | - |
| Ingest | /ingest | - |
| Metrics | /metrics | - |
| Status | /status | - |

**No orphan pages found** - all pages are accessible via routing.

---

### Recommendations

#### Immediate Actions

1. **Fix security vulnerabilities:**
   ```bash
   cd apps/web
   npm audit fix --force
   ```

2. **Update baseline-browser-mapping:**
   ```bash
   npm i baseline-browser-mapping@latest -D
   ```

#### Code Cleanup

1. **Review orphan components** (~3,910 lines)
   - Decide: integrate, archive, or delete
   - Components in mobile/ and workflow/ suggest planned features

2. **Consider archiving:**
   ```bash
   mkdir -p apps/web/src/archive
   mv apps/web/src/components/mobile apps/web/src/archive/
   mv apps/web/src/components/help apps/web/src/archive/
   mv apps/web/src/components/approval apps/web/src/archive/
   mv apps/web/src/components/review apps/web/src/archive/
   ```

---

### Summary Statistics

```
Frontend Build:           SUCCESS
TypeScript Errors:        0
Pages:                    18 (15 unique routes)
Components (total):       26
Components (active):      15
Components (orphan):      11 (~3,910 lines)
Vulnerabilities:          2 (CRITICAL: update next.js)
```
