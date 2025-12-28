# KASHAT PIPELINE AUDIT REPORT

**Audit Date:** December 27, 2025
**Audited Files:** imports.py, ai_workflow.py, recurring.py, transfers.py, p2p_detection.py

---

## Current Pipeline Sequence

### Import Stage (imports.py)
| Step | File | Function | Status |
|------|------|----------|--------|
| 1.1 | imports.py | `import_pdf` / `import_csv` / `import_bulk` | Implemented |
| 1.2 | ingest_pdf.py / ingest_csv.py | `import_pdf_upload` / `import_csv_upload` | Implemented |
| 1.3 | normalization.py | Normalization | Implemented |
| 1.4 | dedup.py | Fingerprint generation | Implemented |

### AI Workflow Stage (ai_workflow.py)
| Step | Stage | Function | Status |
|------|-------|----------|--------|
| 2.1 | IMPORT | `_get_import_transactions` | Implemented |
| 2.2 | AI_ENHANCEMENT | `_enhance_transactions_with_ai` | Implemented |
| 2.3 | RULE_APPLICATION | `_apply_smart_categorization` | Implemented |
| 2.4 | DUPLICATE_DETECTION | `_detect_and_handle_duplicates` | Implemented |
| 2.5 | QUALITY_VALIDATION | `_validate_workflow_quality` | Implemented |
| 2.6 | COMPLETION | `_complete_workflow` | Implemented |

### Built-in Detectors (_run_builtin_detectors)
| Step | Detection | Status |
|------|-----------|--------|
| 3.1 | Zelle tagging | Implemented |
| 3.2 | Income detection | Implemented |
| 3.3 | Adjustment detection | Implemented |
| 3.4 | Recurring detection | Implemented |

---

## Pipeline Order Assessment

| Order | Expected Stage | Actual Stage | Correct? |
|-------|---------------|--------------|----------|
| 1 | Import | Import | YES |
| 2 | Deduplicate | Deduplicate (fingerprint) | YES |
| 3 | Categorize | AI Enhancement + Rule Application | YES |
| 4 | Transfer Detection | NOT IN AUTO PIPELINE | **NO** |
| 5 | P2P Detection | Zelle only (partial) | **PARTIAL** |
| 6 | Recurring Detection | Recurring detection | YES |
| 7 | Enrichment | Income/Adjustment detection | YES |
| 8 | Quality Check | Quality validation | YES |

---

## Issues Found

### Issue 1: Transfer Detection Not Automated
**Current behavior:** Transfer detection runs only on-demand via `/api/transfers/suggest_v2` or `/api/transfers/suggest_v3`

**Expected behavior:** Should run automatically after import, BEFORE recurring detection

**Impact:**
- Recurring detection may incorrectly include transfer pairs as subscriptions
- Users must manually run transfer detection

**Fix required:** Add transfer detection to `_run_builtin_detectors()`:
```python
# In _run_builtin_detectors()
from ...transfers import suggest_transfers_v2
try:
    suggest_transfers_v2()
    print("Transfer detection completed")
except Exception as e:
    print(f"Transfer detection error (non-fatal): {e}")
```

### Issue 2: P2P Detection Incomplete
**Current behavior:** Only Zelle tagging runs automatically (via `parse_zelle_descriptor`)

**Expected behavior:** Full P2P detection for Venmo, Cash App, PayPal, Western Union, Wire

**Impact:**
- Only Zelle transactions are auto-tagged
- Other P2P platforms require manual detection run

**Fix required:** Add full P2P detection to `_run_builtin_detectors()`:
```python
# In _run_builtin_detectors()
from ...p2p_detection import run_p2p_detection
try:
    run_p2p_detection(account_id)
    print("P2P detection completed")
except Exception as e:
    print(f"P2P detection error (non-fatal): {e}")
```

### Issue 3: Pipeline Order Dependency
**Current behavior:** Recurring detection runs after Zelle tagging but not after full P2P/transfer detection

**Expected behavior:**
1. Transfer detection MUST run BEFORE recurring
2. P2P detection SHOULD run BEFORE recurring
3. This prevents P2P/transfer transactions from being classified as recurring payments

**Impact:** Moderate - some P2P recurring payments (like Venmo payments to same person monthly) could be misclassified

---

## Recommendations

### Critical (Fix Required)
1. **Add transfer detection to auto-pipeline**
   - File: `apps/backend/src/kashat/api/routes/imports.py`
   - Function: `_run_builtin_detectors()`
   - Add: `suggest_transfers_v2()` call

2. **Add full P2P detection to auto-pipeline**
   - File: `apps/backend/src/kashat/api/routes/imports.py`
   - Function: `_run_builtin_detectors()`
   - Add: Full P2P detection call

### High Priority
3. **Ensure pipeline order**
   - Transfer detection runs BEFORE recurring
   - P2P detection runs BEFORE recurring
   - Current order is correct if added

### Medium Priority
4. **Create PipelineOrchestrator class**
   - Centralizes pipeline logic
   - Makes order explicit
   - Enables progress tracking

5. **Add pipeline status to import run**
   - Track which stages completed
   - Enable resume on failure

---

## Proposed Pipeline Order

```
┌─────────────────────────────────────────────────────────────────┐
│                    KASHAT PIPELINE SEQUENCE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. IMPORT STAGE (automated)                                     │
│     ├── File Upload (CSV/PDF)                                    │
│     ├── File Parsing (extract raw transactions)                  │
│     ├── Normalization (dates, amounts, descriptions)             │
│     └── Fingerprint Generation (unique ID per transaction)       │
│                                                                  │
│  2. DEDUPLICATION STAGE (automated)                              │
│     ├── Check fingerprint against existing                       │
│     ├── AI duplicate detection                                   │
│     └── Mark/skip duplicates                                     │
│                                                                  │
│  3. AI ENHANCEMENT STAGE (automated if enabled)                  │
│     ├── Merchant name extraction                                 │
│     ├── Confidence scoring                                       │
│     └── Quality assessment                                       │
│                                                                  │
│  4. CATEGORIZATION STAGE (automated if enabled)                  │
│     ├── Check merchant memory (learned patterns)                 │
│     ├── Check rules engine (user-defined rules)                  │
│     └── AI categorization (LLM fallback)                         │
│                                                                  │
│  5. TRANSFER DETECTION STAGE  ⚠️ NEEDS AUTOMATION                │
│     ├── Find matching pairs (same amount, opposite sign)         │
│     ├── Apply V2/V3 algorithms                                   │
│     └── Mark as internal transfers                               │
│                                                                  │
│  6. P2P DETECTION STAGE  ⚠️ NEEDS FULL AUTOMATION                │
│     ├── Pattern matching (Zelle, Venmo, CashApp, etc.)           │
│     ├── Extract counterparty names                               │
│     └── Classify P2P type                                        │
│                                                                  │
│  7. RECURRING DETECTION STAGE (automated)                        │
│     ├── Group by merchant/description                            │
│     ├── Calculate intervals                                      │
│     ├── Detect cadence (monthly, weekly, etc.)                   │
│     └── Create recurring series                                  │
│                                                                  │
│  8. ENRICHMENT STAGE (automated)                                 │
│     ├── Income detection                                         │
│     ├── Adjustment detection                                     │
│     └── Zelle tagging                                            │
│                                                                  │
│  9. QUALITY STAGE (automated)                                    │
│     ├── Data quality scoring                                     │
│     └── Issue flagging                                           │
│                                                                  │
│ 10. INSIGHTS STAGE (on-demand)                                   │
│     ├── Spending pattern analysis                                │
│     ├── Price change detection                                   │
│     └── Generate insight cards                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary

| Category | Count |
|----------|-------|
| Stages Implemented | 10 |
| Stages Automated | 8 |
| Stages On-Demand Only | 2 (Transfer, Full P2P) |
| Order Issues | 0 (if automated) |
| Missing Automation | 2 |

**Pipeline Health: 80%** (8/10 stages automated)

**Action Required:** Add transfer and P2P detection to automatic pipeline

---

**Report Generated:** December 27, 2025
**Audit Duration:** ~15 minutes
