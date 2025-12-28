# KASHAT FULL WORKFLOW VALIDATION PROMPT
## For Claude Code CLI

---

## MISSION

You are validating the newly refactored Kashat personal finance app by:
1. Clearing all existing data (fresh start)
2. Importing real bank statements from the `bank` folder
3. Running ALL pipelines (categorization, transfer detection, recurring, etc.)
4. Monitoring and fixing any issues
5. Evaluating accuracy of results

**Location**: `C:\Users\Marwan\Desktop\AI\Flos`
**Bank Statements**: `C:\Users\Marwan\Desktop\AI\Flos\bank` (or locate if different)

---

## PHASE 1: PREPARATION

### 1.1 Locate Bank Statements

```bash
# Find the bank folder
dir /s /b "C:\Users\Marwan\Desktop\AI\Flos\bank"

# If not found, search common locations
dir /s /b "C:\Users\Marwan\*.csv" | findstr -i "bank\|statement"
dir /s /b "C:\Users\Marwan\*.pdf" | findstr -i "bank\|statement"
```

**Document what you find:**
- [ ] Number of CSV files
- [ ] Number of PDF files
- [ ] Date ranges covered
- [ ] Which banks/accounts

### 1.2 Verify App is Running

```bash
# Check if backend is running
curl http://localhost:8000/health

# If not running, start it:
cd apps/backend
python -m uvicorn kashat.api:app --host 0.0.0.0 --port 8000
```

### 1.3 Document Current State (Before Clear)

```bash
# Get current counts before clearing
curl http://localhost:8000/api/stats
curl http://localhost:8000/api/transactions?limit=1
curl http://localhost:8000/api/accounts
```

Record:
- Total transactions before: ___
- Total accounts before: ___
- Date range before: ___

---

## PHASE 2: CLEAR ALL DATA

### 2.1 Create Backup First

```bash
# Backup current database
copy "apps\backend\data\kashat.db" "apps\backend\data\kashat_backup_%date:~-4%%date:~4,2%%date:~7,2%.db"
```

### 2.2 Clear Database

**Option A: Via API (if endpoint exists)**
```bash
curl -X POST http://localhost:8000/api/admin/reset
```

**Option B: Direct SQL**
```python
import sqlite3

conn = sqlite3.connect('apps/backend/data/kashat.db')
cursor = conn.cursor()

# Clear in correct order (foreign keys)
tables_to_clear = [
    'transaction_category',
    'transaction_rule_match',
    'p2p_transaction',
    'transfer_match',
    'recurring_series_transaction',
    'recurring_series',
    'merchant_category_mapping',
    'import_run_transaction',
    'import_run',
    'transaction',
    'account',
    'budget_category',
    'budget_period',
    'budget',
]

for table in tables_to_clear:
    try:
        cursor.execute(f'DELETE FROM {table}')
        print(f'Cleared {table}: {cursor.rowcount} rows')
    except Exception as e:
        print(f'Error clearing {table}: {e}')

conn.commit()
conn.close()
```

### 2.3 Verify Clean State

```bash
curl http://localhost:8000/api/transactions?limit=1
# Should return empty list

curl http://localhost:8000/api/accounts
# Should return empty list
```

---

## PHASE 3: IMPORT STATEMENTS

### 3.1 List Available Statements

```bash
dir "C:\Users\Marwan\Desktop\AI\Flos\bank" /b
```

### 3.2 Import Each Statement

**For CSV files:**
```bash
# Import via API
curl -X POST http://localhost:8000/api/import/upload \
  -F "file=@C:\Users\Marwan\Desktop\AI\Flos\bank\FILENAME.csv" \
  -F "account_name=ACCOUNT_NAME"
```

**For PDF files:**
```bash
curl -X POST http://localhost:8000/api/import/upload \
  -F "file=@C:\Users\Marwan\Desktop\AI\Flos\bank\FILENAME.pdf" \
  -F "account_name=ACCOUNT_NAME"
```

**Import ALL files systematically:**
```python
import os
import requests

bank_folder = r"C:\Users\Marwan\Desktop\AI\Flos\bank"
api_url = "http://localhost:8000/api/import/upload"

results = []

for filename in os.listdir(bank_folder):
    filepath = os.path.join(bank_folder, filename)
    
    if filename.lower().endswith(('.csv', '.pdf')):
        # Infer account name from filename
        account_name = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
        
        print(f"\n{'='*50}")
        print(f"Importing: {filename}")
        print(f"Account: {account_name}")
        
        with open(filepath, 'rb') as f:
            response = requests.post(
                api_url,
                files={'file': (filename, f)},
                data={'account_name': account_name}
            )
        
        result = {
            'filename': filename,
            'status': response.status_code,
            'response': response.json() if response.ok else response.text
        }
        results.append(result)
        
        if response.ok:
            data = response.json()
            print(f"✅ Success: {data.get('transactions_imported', 0)} transactions")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)

# Summary
print("\n" + "="*50)
print("IMPORT SUMMARY")
print("="*50)
for r in results:
    status = "✅" if r['status'] == 200 else "❌"
    print(f"{status} {r['filename']}: {r['status']}")
```

### 3.3 Monitor Import Progress

After each import, check:
```bash
# Check import run status
curl http://localhost:8000/api/import/runs

# Check transaction count
curl http://localhost:8000/api/stats
```

### 3.4 Log Any Import Errors

Create a log of any issues:
```
IMPORT_LOG.md
- File: xxx.csv
- Error: xxx
- Fix applied: xxx
```

---

## PHASE 4: RUN ALL PIPELINES

### 4.1 AI Categorization Pipeline

```bash
# Trigger AI categorization for uncategorized transactions
curl -X POST http://localhost:8000/api/ai/categorize/bulk \
  -H "Content-Type: application/json" \
  -d '{"limit": 500}'
```

**Monitor progress:**
```bash
# Check how many still need categorization
curl "http://localhost:8000/api/transactions?uncategorized=true&limit=1"
```

### 4.2 Transfer Detection Pipeline

```bash
# Run transfer detection
curl -X POST http://localhost:8000/api/transfers/detect
```

**Check results:**
```bash
curl http://localhost:8000/api/transfers
curl http://localhost:8000/api/transfers/stats
```

### 4.3 Recurring Detection Pipeline

```bash
# Run recurring detection
curl -X POST http://localhost:8000/api/recurring/detect
```

**Check results:**
```bash
curl http://localhost:8000/api/recurring
curl http://localhost:8000/api/recurring/stats
```

### 4.4 P2P Detection Pipeline

```bash
# Run P2P detection (if endpoint exists)
curl -X POST http://localhost:8000/api/p2p/detect
```

**Check results:**
```bash
curl http://localhost:8000/api/p2p
```

### 4.5 Data Quality Pipeline

```bash
# Run data quality checks
curl -X POST http://localhost:8000/api/quality/analyze
```

**Check results:**
```bash
curl http://localhost:8000/api/quality/score
curl http://localhost:8000/api/quality/issues
```

### 4.6 Insights Generation

```bash
# Generate insight cards
curl http://localhost:8000/api/insights/cards
```

---

## PHASE 5: FIX ISSUES

### Common Issues and Fixes

**Issue: Import fails with parsing error**
```python
# Check the CSV format
import pandas as pd
df = pd.read_csv('problem_file.csv')
print(df.columns)
print(df.head())
# Identify date format, amount format issues
```

**Issue: Categorization not running**
```bash
# Check AI provider status
curl http://localhost:8000/api/ai/status

# Check if LM Studio is running
curl http://localhost:1234/v1/models
```

**Issue: Transfer detection finds too many/few**
```bash
# Check transfer detection settings
curl http://localhost:8000/api/settings/transfer-detection

# Adjust thresholds if needed
curl -X PUT http://localhost:8000/api/settings/transfer-detection \
  -H "Content-Type: application/json" \
  -d '{"similarity_threshold": 0.85}'
```

**Issue: Recurring detection misses subscriptions**
```bash
# Check recurring settings
curl http://localhost:8000/api/settings/recurring-detection

# Run with lower threshold
curl -X POST http://localhost:8000/api/recurring/detect \
  -H "Content-Type: application/json" \
  -d '{"min_occurrences": 2}'
```

### Log All Fixes Applied

```markdown
## FIXES_LOG.md

### Issue 1: [Description]
- Error: [Error message]
- Root cause: [Analysis]
- Fix applied: [What you did]
- Result: [Outcome]

### Issue 2: ...
```

---

## PHASE 6: EVALUATE RESULTS

### 6.1 Overall Statistics

```bash
# Get comprehensive stats
curl http://localhost:8000/api/stats
```

**Record:**
| Metric | Value |
|--------|-------|
| Total Transactions | ___ |
| Total Accounts | ___ |
| Date Range | ___ to ___ |
| Categorized | ___% |
| Transfers Detected | ___ |
| Recurring Series | ___ |
| P2P Transactions | ___ |

### 6.2 Categorization Accuracy

**Sample 50 random transactions and verify:**
```python
import requests
import random

# Get all transactions
response = requests.get("http://localhost:8000/api/transactions?limit=1000")
transactions = response.json()['items']

# Sample 50 random
sample = random.sample(transactions, min(50, len(transactions)))

# Manual review
accuracy_log = []
for tx in sample:
    print(f"\n{'='*50}")
    print(f"Date: {tx['posted_at']}")
    print(f"Description: {tx['description']}")
    print(f"Amount: ${tx['amount']}")
    print(f"Category: {tx.get('category_name', 'UNCATEGORIZED')}")
    print(f"AI Confidence: {tx.get('ai_confidence', 'N/A')}")
    
    # Record your assessment
    # correct = input("Correct? (y/n): ")
    # accuracy_log.append({'tx_id': tx['id'], 'correct': correct == 'y'})

# Calculate accuracy
# correct_count = sum(1 for x in accuracy_log if x['correct'])
# accuracy = correct_count / len(accuracy_log) * 100
# print(f"\nCategorization Accuracy: {accuracy:.1f}%")
```

### 6.3 Transfer Detection Accuracy

```python
# Get all detected transfers
response = requests.get("http://localhost:8000/api/transfers")
transfers = response.json()

print(f"Total transfers detected: {len(transfers)}")

# Review each
for t in transfers[:20]:  # Review first 20
    print(f"\n{'='*50}")
    print(f"From: {t['from_description']} (${t['from_amount']})")
    print(f"To: {t['to_description']} (${t['to_amount']})")
    print(f"Confidence: {t.get('confidence', 'N/A')}")
    # Verify if this is actually a transfer
```

**Metrics to calculate:**
- True Positives: Correctly identified transfers
- False Positives: Non-transfers marked as transfers
- False Negatives: Missed transfers (check manually)
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)

### 6.4 Recurring Detection Accuracy

```python
# Get all recurring series
response = requests.get("http://localhost:8000/api/recurring")
series = response.json()

print(f"Total recurring series: {len(series)}")

for s in series:
    print(f"\n{'='*50}")
    print(f"Name: {s['name']}")
    print(f"Merchant: {s.get('merchant', 'N/A')}")
    print(f"Amount: ${s['amount_mean']:.2f} (±${s.get('amount_std', 0):.2f})")
    print(f"Cadence: {s['recurring_type']}")
    print(f"Transactions: {s['transaction_count']}")
    print(f"Next Expected: {s.get('next_date', 'N/A')}")
```

**Verify:**
- [ ] Netflix detected
- [ ] Spotify detected
- [ ] Phone bill detected
- [ ] Rent/mortgage detected
- [ ] Car payment detected
- [ ] Insurance detected
- [ ] Gym membership detected

### 6.5 Business vs Personal Accuracy

```bash
# Check business transaction detection
curl "http://localhost:8000/api/transactions?is_business=true&limit=20"
```

### 6.6 Create Accuracy Report

```markdown
## KASHAT_ACCURACY_REPORT.md

### Test Date: [DATE]
### Statements Imported: [COUNT]
### Transaction Count: [COUNT]
### Date Range: [START] to [END]

---

## Categorization

| Metric | Value |
|--------|-------|
| Total Categorized | ___% |
| Sample Size | 50 |
| Correct | ___ |
| Incorrect | ___ |
| **Accuracy** | **___%** |

### Common Misclassifications:
1. [Description] → Was: [Category] → Should be: [Category]
2. ...

---

## Transfer Detection

| Metric | Value |
|--------|-------|
| Detected | ___ |
| True Positives | ___ |
| False Positives | ___ |
| Estimated False Negatives | ___ |
| **Precision** | **___%** |
| **Recall** | **___%** |

---

## Recurring Detection

| Metric | Value |
|--------|-------|
| Series Detected | ___ |
| Correct | ___ |
| Incorrect/Spurious | ___ |
| **Accuracy** | **___%** |

### Known Subscriptions Status:
| Service | Detected? | Correct Amount? | Correct Cadence? |
|---------|-----------|-----------------|------------------|
| Netflix | ✅/❌ | ✅/❌ | ✅/❌ |
| Spotify | ✅/❌ | ✅/❌ | ✅/❌ |
| ... | | | |

---

## Data Quality

| Metric | Value |
|--------|-------|
| Quality Score | ___/100 |
| Duplicates Found | ___ |
| Missing Data | ___ |
| Anomalies | ___ |

---

## New Features Validation

| Feature | Working? | Notes |
|---------|----------|-------|
| Net Worth | ✅/❌ | |
| Bill Calendar | ✅/❌ | |
| Budget System | ✅/❌ | |
| Insight Cards | ✅/❌ | |
| Transaction Review | ✅/❌ | |

---

## Issues Found

1. **[Issue Title]**
   - Severity: High/Medium/Low
   - Description: ...
   - Recommended Fix: ...

---

## Overall Assessment

**Categorization**: [EXCELLENT/GOOD/NEEDS IMPROVEMENT]
**Transfer Detection**: [EXCELLENT/GOOD/NEEDS IMPROVEMENT]
**Recurring Detection**: [EXCELLENT/GOOD/NEEDS IMPROVEMENT]
**Data Quality**: [EXCELLENT/GOOD/NEEDS IMPROVEMENT]

**Ready for Production**: ✅ YES / ❌ NO (needs fixes)
```

---

## PHASE 7: GENERATE FINAL REPORT

### 7.1 Create Summary

After all evaluations, produce:

1. **IMPORT_SUMMARY.md** - What was imported
2. **FIXES_LOG.md** - Issues found and fixed
3. **KASHAT_ACCURACY_REPORT.md** - Full accuracy evaluation
4. **RECOMMENDATIONS.md** - Suggested improvements

### 7.2 Dashboard Verification

Open the frontend and verify:
- [ ] Dashboard loads without errors
- [ ] Net worth displays correctly
- [ ] Insight cards appear
- [ ] Calendar shows upcoming bills
- [ ] Transactions list properly
- [ ] Analytics charts render
- [ ] Budget page works (if budget created)

### 7.3 Screenshot Key Screens

Take screenshots of:
- Dashboard
- Calendar with bills
- Analytics
- Any errors encountered

---

## EXECUTION CHECKLIST

```
[ ] Phase 1: Preparation complete
    [ ] Bank folder located
    [ ] App running
    [ ] Current state documented

[ ] Phase 2: Data cleared
    [ ] Backup created
    [ ] All tables cleared
    [ ] Clean state verified

[ ] Phase 3: Import complete
    [ ] All CSV files imported
    [ ] All PDF files imported
    [ ] Import errors logged

[ ] Phase 4: Pipelines run
    [ ] Categorization complete
    [ ] Transfer detection complete
    [ ] Recurring detection complete
    [ ] P2P detection complete
    [ ] Quality analysis complete
    [ ] Insights generated

[ ] Phase 5: Issues fixed
    [ ] All errors resolved
    [ ] Fixes documented

[ ] Phase 6: Evaluation complete
    [ ] Statistics gathered
    [ ] Categorization accuracy measured
    [ ] Transfer accuracy measured
    [ ] Recurring accuracy measured
    [ ] New features verified

[ ] Phase 7: Reports generated
    [ ] All reports created
    [ ] Dashboard verified
    [ ] Screenshots taken
```

---

## SUCCESS CRITERIA

| Metric | Target | Actual |
|--------|--------|--------|
| Import Success Rate | 100% | ___ |
| Categorization Coverage | >95% | ___ |
| Categorization Accuracy | >85% | ___ |
| Transfer Precision | >90% | ___ |
| Recurring Detection | >80% | ___ |
| Data Quality Score | >80 | ___ |
| New Features Working | 5/5 | ___ |
| Dashboard Errors | 0 | ___ |

---

*Execute methodically. Log everything. Fix issues as you find them. Produce the final accuracy report.*
