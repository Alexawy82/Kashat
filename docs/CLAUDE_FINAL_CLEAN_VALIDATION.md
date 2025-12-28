# KASHAT FINAL VALIDATION - CLEAN RUN
## For Claude Code CLI

---

## MISSION

Now that all pipeline fixes are in place, we need to:
1. **Clear ALL data** (fresh start)
2. **Import ALL statements** from bank folder
3. **Let the FULL pipeline run** with correct sequence
4. **Deep analysis** of every detection result

**Location**: `C:\Users\Marwan\Desktop\AI\Flos`
**Bank Statements**: `C:\Users\Marwan\Desktop\AI\Flos\bank`

---

## PHASE 1: COMPLETE DATA CLEAR

### 1.1 Backup Current Database

```bash
# Create timestamped backup
copy "apps\backend\data\kashat.db" "apps\backend\data\kashat_backup_final_%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%.db"
```

### 1.2 Clear ALL Tables

```python
import sqlite3
from datetime import datetime

db_path = 'apps/backend/data/kashat.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in cursor.fetchall()]

print(f"Found {len(tables)} tables to clear")
print(f"Clearing at: {datetime.now()}")
print("="*50)

# Tables to preserve (system tables)
preserve = ['category', 'rule']  # Keep categories and rules

# Clear order matters for foreign keys
clear_order = [
    # Junction/child tables first
    'transaction_category',
    'transaction_rule_match', 
    'recurring_series_transaction',
    'import_run_transaction',
    'budget_category',
    'budget_period',
    # Detection results
    'transfer_match',
    'p2p_transaction',
    'recurring_series',
    # Core data
    'transaction',
    'import_run',
    'account',
    'budget',
    # Learned data (optional - decide if keeping)
    'merchant_category_mapping',
]

cleared = {}
for table in clear_order:
    if table in tables and table not in preserve:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count_before = cursor.fetchone()[0]
            cursor.execute(f'DELETE FROM {table}')
            cleared[table] = count_before
            print(f"✓ {table}: {count_before} rows deleted")
        except Exception as e:
            print(f"✗ {table}: ERROR - {e}")

# Check for any tables we missed
for table in tables:
    if table not in clear_order and table not in preserve:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"⚠ {table}: {count} rows (NOT CLEARED - add to list if needed)")

conn.commit()
conn.close()

print("="*50)
print(f"Total rows cleared: {sum(cleared.values())}")
print("Data clear complete!")
```

### 1.3 Verify Clean State

```bash
# Via API
curl http://localhost:8000/api/transactions?limit=1
# Expected: {"items": [], "total": 0, ...}

curl http://localhost:8000/api/accounts
# Expected: []

curl http://localhost:8000/api/recurring
# Expected: []

curl http://localhost:8000/api/p2p
# Expected: []

curl http://localhost:8000/api/transfers
# Expected: []
```

**Confirm:**
- [ ] 0 transactions
- [ ] 0 accounts
- [ ] 0 recurring series
- [ ] 0 P2P transactions
- [ ] 0 transfer matches

---

## PHASE 2: IMPORT ALL STATEMENTS

### 2.1 List Available Statements

```python
import os

bank_folder = r"C:\Users\Marwan\Desktop\AI\Flos\bank"

files = []
for f in os.listdir(bank_folder):
    filepath = os.path.join(bank_folder, f)
    if f.lower().endswith(('.csv', '.pdf')):
        size = os.path.getsize(filepath)
        files.append({
            'name': f,
            'type': f.split('.')[-1].upper(),
            'size_kb': size / 1024
        })

print(f"Found {len(files)} statement files:")
print("="*60)
for f in sorted(files, key=lambda x: x['name']):
    print(f"  {f['type']:4} | {f['size_kb']:7.1f} KB | {f['name']}")
```

### 2.2 Import Each Statement with Logging

```python
import os
import requests
import time
from datetime import datetime

bank_folder = r"C:\Users\Marwan\Desktop\AI\Flos\bank"
api_url = "http://localhost:8000/api/import/upload"

results = []
total_start = time.time()

print(f"\n{'='*70}")
print(f"KASHAT IMPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}\n")

for filename in sorted(os.listdir(bank_folder)):
    if not filename.lower().endswith(('.csv', '.pdf')):
        continue
    
    filepath = os.path.join(bank_folder, filename)
    
    # Infer account name from filename
    # Adjust this logic based on your file naming convention
    account_name = filename.replace('.pdf', '').replace('.csv', '').replace('_', ' ')
    
    print(f"\n{'─'*50}")
    print(f"📄 Importing: {filename}")
    print(f"   Account: {account_name}")
    
    start = time.time()
    
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                api_url,
                files={'file': (filename, f)},
                data={'account_name': account_name},
                timeout=120  # 2 min timeout for large files
            )
        
        elapsed = time.time() - start
        
        if response.ok:
            data = response.json()
            result = {
                'filename': filename,
                'account': account_name,
                'status': 'SUCCESS',
                'transactions': data.get('transactions_imported', 0),
                'duplicates': data.get('duplicates_skipped', 0),
                'import_run_id': data.get('import_run_id'),
                'elapsed': elapsed,
                'error': None
            }
            print(f"   ✅ SUCCESS: {result['transactions']} transactions ({result['duplicates']} duplicates)")
            print(f"   ⏱️ Time: {elapsed:.1f}s")
        else:
            result = {
                'filename': filename,
                'account': account_name,
                'status': 'FAILED',
                'transactions': 0,
                'duplicates': 0,
                'import_run_id': None,
                'elapsed': elapsed,
                'error': response.text[:200]
            }
            print(f"   ❌ FAILED: {response.status_code}")
            print(f"   Error: {result['error']}")
    
    except Exception as e:
        result = {
            'filename': filename,
            'account': account_name,
            'status': 'ERROR',
            'transactions': 0,
            'duplicates': 0,
            'import_run_id': None,
            'elapsed': 0,
            'error': str(e)
        }
        print(f"   ❌ ERROR: {e}")
    
    results.append(result)

total_elapsed = time.time() - total_start

# Summary
print(f"\n{'='*70}")
print(f"IMPORT SUMMARY")
print(f"{'='*70}")

successful = [r for r in results if r['status'] == 'SUCCESS']
failed = [r for r in results if r['status'] != 'SUCCESS']

print(f"\nFiles: {len(successful)}/{len(results)} successful")
print(f"Total transactions: {sum(r['transactions'] for r in results)}")
print(f"Total duplicates skipped: {sum(r['duplicates'] for r in results)}")
print(f"Total time: {total_elapsed:.1f}s")

if failed:
    print(f"\n⚠️ FAILED IMPORTS:")
    for r in failed:
        print(f"   - {r['filename']}: {r['error']}")

# Save results for analysis
import json
with open('import_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to import_results.json")
```

### 2.3 Verify Import Counts

```bash
# Get total counts after import
curl http://localhost:8000/api/stats
```

**Record:**
- Total transactions: ___
- Total accounts: ___
- Date range: ___ to ___

---

## PHASE 3: VERIFY PIPELINE EXECUTION

The pipeline should have run automatically during import. Let's verify each stage executed.

### 3.1 Check Pipeline Logs

```python
import requests

# Get recent import runs
runs = requests.get("http://localhost:8000/api/import/runs?limit=20").json()

print(f"Import runs: {len(runs)}")
print("="*60)

for run in runs:
    print(f"\nRun: {run.get('id', 'N/A')[:8]}...")
    print(f"  File: {run.get('filename', 'N/A')}")
    print(f"  Status: {run.get('status', 'N/A')}")
    print(f"  Transactions: {run.get('transactions_imported', 0)}")
    print(f"  Started: {run.get('started_at', 'N/A')}")
    print(f"  Completed: {run.get('completed_at', 'N/A')}")
    
    # Check if pipeline stages ran
    stages = run.get('pipeline_stages', {})
    if stages:
        print(f"  Pipeline stages:")
        for stage, result in stages.items():
            status = "✅" if result.get('success') else "❌"
            print(f"    {status} {stage}: {result.get('count', 'N/A')}")
```

### 3.2 Verify Each Detection Ran

```python
import requests

print("="*60)
print("PIPELINE DETECTION RESULTS")
print("="*60)

# 1. Categorization
tx_response = requests.get("http://localhost:8000/api/transactions?limit=1").json()
total_tx = tx_response.get('total', 0)

categorized = requests.get("http://localhost:8000/api/transactions?has_category=true&limit=1").json()
cat_count = categorized.get('total', 0)

print(f"\n📁 CATEGORIZATION")
print(f"   Categorized: {cat_count}/{total_tx} ({cat_count/total_tx*100:.1f}%)")

# 2. Transfer Detection
transfers = requests.get("http://localhost:8000/api/transfers").json()
transfer_count = len(transfers) if isinstance(transfers, list) else transfers.get('total', 0)
print(f"\n🔄 TRANSFER DETECTION")
print(f"   Transfer pairs found: {transfer_count}")

# 3. P2P Detection
p2p = requests.get("http://localhost:8000/api/p2p").json()
p2p_count = len(p2p) if isinstance(p2p, list) else p2p.get('total', 0)
print(f"\n👥 P2P DETECTION")
print(f"   P2P transactions: {p2p_count}")

# 4. Recurring Detection
recurring = requests.get("http://localhost:8000/api/recurring").json()
recurring_count = len(recurring) if isinstance(recurring, list) else recurring.get('total', 0)
print(f"\n🔁 RECURRING DETECTION")
print(f"   Recurring series: {recurring_count}")

# 5. Income Detection
income = requests.get("http://localhost:8000/api/transactions?is_income=true&limit=1").json()
income_count = income.get('total', 0)
print(f"\n💵 INCOME DETECTION")
print(f"   Income transactions: {income_count}")

# 6. Business Detection
business = requests.get("http://localhost:8000/api/transactions?is_business=true&limit=1").json()
business_count = business.get('total', 0)
print(f"\n💼 BUSINESS DETECTION")
print(f"   Business transactions: {business_count}")

# Summary
print(f"\n{'='*60}")
print("PIPELINE SUMMARY")
print(f"{'='*60}")
print(f"Total Transactions: {total_tx}")
print(f"Categorized: {cat_count} ({cat_count/total_tx*100:.1f}%)")
print(f"Transfers: {transfer_count} pairs")
print(f"P2P: {p2p_count}")
print(f"Recurring: {recurring_count} series")
print(f"Income: {income_count}")
print(f"Business: {business_count}")
```

---

## PHASE 4: DEEP ANALYSIS

### 4.1 Account Analysis

```python
import requests

accounts = requests.get("http://localhost:8000/api/accounts").json()

print("="*70)
print("ACCOUNT ANALYSIS")
print("="*70)

total_assets = 0
total_liabilities = 0

for acc in accounts:
    name = acc.get('name', 'Unknown')
    acc_type = acc.get('account_type', 'unknown')
    balance = acc.get('balance', 0)
    tx_count = acc.get('transaction_count', 0)
    
    # Classify for net worth
    if acc_type in ['credit_card', 'loan']:
        total_liabilities += abs(balance)
        category = "LIABILITY"
    else:
        total_assets += balance
        category = "ASSET"
    
    print(f"\n📊 {name}")
    print(f"   Type: {acc_type} ({category})")
    print(f"   Balance: ${balance:,.2f}")
    print(f"   Transactions: {tx_count}")

print(f"\n{'─'*50}")
print(f"NET WORTH CALCULATION")
print(f"{'─'*50}")
print(f"Total Assets: ${total_assets:,.2f}")
print(f"Total Liabilities: ${total_liabilities:,.2f}")
print(f"NET WORTH: ${total_assets - total_liabilities:,.2f}")
```

### 4.2 Transfer Detection Deep Analysis

```python
import requests
from collections import defaultdict

transfers = requests.get("http://localhost:8000/api/transfers").json()

print("="*70)
print("TRANSFER DETECTION ANALYSIS")
print("="*70)

if not transfers:
    print("\n⚠️ No transfers detected")
    print("   This could mean:")
    print("   - Single account imported (no cross-account transfers possible)")
    print("   - Transfer patterns don't match detection algorithms")
    print("   - Transfers already excluded correctly")
else:
    print(f"\nTotal transfer pairs: {len(transfers)}")
    
    # Analyze by confidence
    by_confidence = defaultdict(list)
    for t in transfers:
        conf = t.get('confidence', 0)
        if conf >= 0.9:
            by_confidence['HIGH (90%+)'].append(t)
        elif conf >= 0.7:
            by_confidence['MEDIUM (70-90%)'].append(t)
        else:
            by_confidence['LOW (<70%)'].append(t)
    
    print(f"\nBy Confidence:")
    for level, items in by_confidence.items():
        print(f"   {level}: {len(items)}")
    
    # Show sample transfers
    print(f"\nSample Transfers:")
    for t in transfers[:5]:
        print(f"\n   From: {t.get('from_description', 'N/A')[:40]}")
        print(f"   To: {t.get('to_description', 'N/A')[:40]}")
        print(f"   Amount: ${abs(t.get('amount', 0)):,.2f}")
        print(f"   Confidence: {t.get('confidence', 0)*100:.0f}%")
        print(f"   Algorithm: {t.get('algorithm', 'N/A')}")
```

### 4.3 P2P Detection Deep Analysis

```python
import requests
from collections import Counter

p2p = requests.get("http://localhost:8000/api/p2p").json()

print("="*70)
print("P2P DETECTION ANALYSIS")
print("="*70)

if not p2p:
    print("\n⚠️ No P2P transactions detected")
else:
    print(f"\nTotal P2P transactions: {len(p2p)}")
    
    # By platform
    platforms = Counter(t.get('platform', 'unknown') for t in p2p)
    print(f"\nBy Platform:")
    for platform, count in platforms.most_common():
        pct = count / len(p2p) * 100
        print(f"   {platform}: {count} ({pct:.1f}%)")
    
    # By direction
    directions = Counter(t.get('direction', 'unknown') for t in p2p)
    print(f"\nBy Direction:")
    for direction, count in directions.most_common():
        print(f"   {direction}: {count}")
    
    # Top counterparties
    counterparties = Counter(t.get('counterparty', 'unknown') for t in p2p)
    print(f"\nTop 10 Counterparties:")
    for cp, count in counterparties.most_common(10):
        print(f"   {cp}: {count} transactions")
    
    # Total volume
    total_sent = sum(abs(t.get('amount', 0)) for t in p2p if t.get('direction') == 'sent')
    total_received = sum(abs(t.get('amount', 0)) for t in p2p if t.get('direction') == 'received')
    print(f"\nP2P Volume:")
    print(f"   Sent: ${total_sent:,.2f}")
    print(f"   Received: ${total_received:,.2f}")
    print(f"   Net: ${total_received - total_sent:,.2f}")
```

### 4.4 Recurring Detection Deep Analysis

```python
import requests
from collections import Counter
from datetime import datetime

recurring = requests.get("http://localhost:8000/api/recurring").json()

print("="*70)
print("RECURRING DETECTION ANALYSIS")  
print("="*70)

if not recurring:
    print("\n⚠️ No recurring series detected")
else:
    print(f"\nTotal recurring series: {len(recurring)}")
    
    # By type/cadence
    cadences = Counter(r.get('recurring_type', 'unknown') for r in recurring)
    print(f"\nBy Cadence:")
    for cadence, count in cadences.most_common():
        print(f"   {cadence}: {count}")
    
    # By category
    categories = Counter(r.get('category_name', 'Uncategorized') for r in recurring)
    print(f"\nBy Category:")
    for cat, count in categories.most_common(10):
        print(f"   {cat}: {count}")
    
    # Monthly cost analysis
    monthly_series = [r for r in recurring if r.get('recurring_type') == 'monthly']
    total_monthly = sum(abs(r.get('amount_mean', 0)) for r in monthly_series)
    print(f"\nMonthly Recurring Cost: ${total_monthly:,.2f}")
    
    # Subscriptions (small monthly charges)
    subscriptions = [r for r in monthly_series if abs(r.get('amount_mean', 0)) < 100]
    sub_total = sum(abs(r.get('amount_mean', 0)) for r in subscriptions)
    print(f"Subscriptions (<$100/mo): {len(subscriptions)} totaling ${sub_total:,.2f}/mo")
    
    # Bills (larger monthly charges)
    bills = [r for r in monthly_series if abs(r.get('amount_mean', 0)) >= 100]
    bill_total = sum(abs(r.get('amount_mean', 0)) for r in bills)
    print(f"Bills (≥$100/mo): {len(bills)} totaling ${bill_total:,.2f}/mo")
    
    # Show all recurring series
    print(f"\n{'─'*60}")
    print("ALL RECURRING SERIES (sorted by amount)")
    print(f"{'─'*60}")
    
    sorted_recurring = sorted(recurring, key=lambda x: abs(x.get('amount_mean', 0)), reverse=True)
    
    for r in sorted_recurring:
        name = r.get('display_name') or r.get('name', 'Unknown')
        amount = abs(r.get('amount_mean', 0))
        cadence = r.get('recurring_type', '?')
        tx_count = r.get('transaction_count', 0)
        next_date = r.get('next_date', 'N/A')
        confidence = r.get('confidence', 0)
        
        # Status indicator
        if confidence >= 0.8:
            status = "✅"
        elif confidence >= 0.5:
            status = "⚠️"
        else:
            status = "❓"
        
        print(f"\n{status} {name[:40]}")
        print(f"   ${amount:,.2f} / {cadence}")
        print(f"   {tx_count} occurrences | Confidence: {confidence*100:.0f}%")
        print(f"   Next: {next_date}")
    
    # Potential issues
    print(f"\n{'─'*60}")
    print("POTENTIAL ISSUES")
    print(f"{'─'*60}")
    
    # Low confidence series
    low_conf = [r for r in recurring if r.get('confidence', 0) < 0.5]
    if low_conf:
        print(f"\n⚠️ Low confidence series ({len(low_conf)}):")
        for r in low_conf[:5]:
            print(f"   - {r.get('name', 'Unknown')}: {r.get('confidence', 0)*100:.0f}%")
    
    # Possibly transfers marked as recurring
    transfer_keywords = ['transfer', 'xfer', 'payment to', 'payment from']
    possible_transfers = [r for r in recurring 
                         if any(kw in r.get('name', '').lower() for kw in transfer_keywords)]
    if possible_transfers:
        print(f"\n⚠️ Possibly transfers in recurring ({len(possible_transfers)}):")
        for r in possible_transfers[:5]:
            print(f"   - {r.get('name', 'Unknown')}")
    
    # P2P marked as recurring
    p2p_keywords = ['zelle', 'venmo', 'cashapp', 'paypal']
    possible_p2p = [r for r in recurring
                   if any(kw in r.get('name', '').lower() for kw in p2p_keywords)]
    if possible_p2p:
        print(f"\n⚠️ Possibly P2P in recurring ({len(possible_p2p)}):")
        for r in possible_p2p[:5]:
            print(f"   - {r.get('name', 'Unknown')}")
```

### 4.5 Category Distribution Analysis

```python
import requests
from collections import Counter

# Get all transactions
all_tx = []
offset = 0
limit = 500

while True:
    response = requests.get(f"http://localhost:8000/api/transactions?limit={limit}&offset={offset}").json()
    items = response.get('items', [])
    if not items:
        break
    all_tx.extend(items)
    offset += limit
    if len(items) < limit:
        break

print("="*70)
print("CATEGORY DISTRIBUTION ANALYSIS")
print("="*70)

print(f"\nTotal transactions analyzed: {len(all_tx)}")

# By category
categories = Counter(tx.get('category_name', 'Uncategorized') for tx in all_tx)

print(f"\nBy Category (count):")
for cat, count in categories.most_common(20):
    pct = count / len(all_tx) * 100
    bar = "█" * int(pct / 2)
    print(f"   {cat[:25]:25} {count:5} ({pct:5.1f}%) {bar}")

# By category (amount)
category_amounts = {}
for tx in all_tx:
    cat = tx.get('category_name', 'Uncategorized')
    amount = tx.get('amount', 0)
    if amount < 0:  # Expenses only
        category_amounts[cat] = category_amounts.get(cat, 0) + abs(amount)

print(f"\nBy Category (spending):")
for cat, amount in sorted(category_amounts.items(), key=lambda x: x[1], reverse=True)[:15]:
    print(f"   {cat[:25]:25} ${amount:>12,.2f}")

# Uncategorized analysis
uncategorized = [tx for tx in all_tx if not tx.get('category_name') or tx.get('category_name') == 'Uncategorized']
print(f"\n{'─'*50}")
print(f"UNCATEGORIZED TRANSACTIONS: {len(uncategorized)}")
print(f"{'─'*50}")

if uncategorized:
    # Sample uncategorized
    print(f"\nSample uncategorized (first 10):")
    for tx in uncategorized[:10]:
        print(f"   {tx.get('posted_at', 'N/A')[:10]} | ${tx.get('amount', 0):>10,.2f} | {tx.get('description', 'N/A')[:40]}")
```

### 4.6 Income Analysis

```python
import requests
from collections import Counter
from datetime import datetime

# Get income transactions
income_response = requests.get("http://localhost:8000/api/transactions?is_income=true&limit=500").json()
income_tx = income_response.get('items', [])

print("="*70)
print("INCOME ANALYSIS")
print("="*70)

print(f"\nTotal income transactions: {len(income_tx)}")

if income_tx:
    total_income = sum(tx.get('amount', 0) for tx in income_tx)
    print(f"Total income: ${total_income:,.2f}")
    
    # By source
    sources = Counter(tx.get('description', 'Unknown')[:30] for tx in income_tx)
    print(f"\nIncome Sources:")
    for source, count in sources.most_common(10):
        source_total = sum(tx.get('amount', 0) for tx in income_tx if tx.get('description', '')[:30] == source)
        print(f"   {source}: {count} deposits, ${source_total:,.2f}")
    
    # By month
    monthly_income = {}
    for tx in income_tx:
        month = tx.get('posted_at', '')[:7]  # YYYY-MM
        monthly_income[month] = monthly_income.get(month, 0) + tx.get('amount', 0)
    
    print(f"\nMonthly Income:")
    for month in sorted(monthly_income.keys()):
        print(f"   {month}: ${monthly_income[month]:,.2f}")
    
    avg_monthly = sum(monthly_income.values()) / len(monthly_income) if monthly_income else 0
    print(f"\nAverage Monthly Income: ${avg_monthly:,.2f}")
```

### 4.7 Spending Pattern Analysis

```python
import requests
from collections import defaultdict
from datetime import datetime

# Get all expense transactions
expenses = []
offset = 0
while True:
    response = requests.get(f"http://localhost:8000/api/transactions?is_income=false&limit=500&offset={offset}").json()
    items = response.get('items', [])
    if not items:
        break
    expenses.extend([tx for tx in items if tx.get('amount', 0) < 0])
    offset += 500
    if len(items) < 500:
        break

print("="*70)
print("SPENDING PATTERN ANALYSIS")
print("="*70)

print(f"\nTotal expense transactions: {len(expenses)}")
total_spent = sum(abs(tx.get('amount', 0)) for tx in expenses)
print(f"Total spent: ${total_spent:,.2f}")

# Monthly spending
monthly_spending = defaultdict(float)
for tx in expenses:
    month = tx.get('posted_at', '')[:7]
    monthly_spending[month] += abs(tx.get('amount', 0))

print(f"\nMonthly Spending:")
for month in sorted(monthly_spending.keys()):
    amount = monthly_spending[month]
    bar = "█" * int(amount / 500)
    print(f"   {month}: ${amount:>10,.2f} {bar}")

avg_monthly = sum(monthly_spending.values()) / len(monthly_spending) if monthly_spending else 0
print(f"\nAverage Monthly Spending: ${avg_monthly:,.2f}")

# Day of week pattern
dow_spending = defaultdict(float)
dow_count = defaultdict(int)
dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

for tx in expenses:
    try:
        date = datetime.fromisoformat(tx.get('posted_at', '')[:10])
        dow = date.weekday()
        dow_spending[dow] += abs(tx.get('amount', 0))
        dow_count[dow] += 1
    except:
        pass

print(f"\nSpending by Day of Week:")
for dow in range(7):
    count = dow_count[dow]
    total = dow_spending[dow]
    avg = total / count if count else 0
    print(f"   {dow_names[dow]}: {count:4} transactions, ${total:>10,.2f} total, ${avg:>8,.2f} avg")

# Top merchants
merchants = defaultdict(lambda: {'count': 0, 'total': 0})
for tx in expenses:
    desc = tx.get('description', 'Unknown')[:30]
    merchants[desc]['count'] += 1
    merchants[desc]['total'] += abs(tx.get('amount', 0))

print(f"\nTop 15 Merchants by Spending:")
sorted_merchants = sorted(merchants.items(), key=lambda x: x[1]['total'], reverse=True)
for merchant, data in sorted_merchants[:15]:
    print(f"   {merchant:30} {data['count']:4} tx  ${data['total']:>10,.2f}")
```

---

## PHASE 5: ACCURACY ASSESSMENT

### 5.1 Recurring Detection Accuracy

```python
import requests

recurring = requests.get("http://localhost:8000/api/recurring").json()

print("="*70)
print("RECURRING DETECTION ACCURACY CHECK")
print("="*70)

# Known subscriptions to look for
known_subscriptions = [
    'netflix', 'spotify', 'amazon prime', 'hulu', 'disney+', 'disney plus',
    'openai', 'chatgpt', 'midjourney', 'github', 'dropbox', 'google', 'youtube',
    'apple', 'icloud', 'microsoft', 'adobe', 'canva',
    'gym', 'fitness', 'planet fitness',
]

# Known bills
known_bills = [
    'electric', 'power', 'energy', 'duke', 'dominion',
    'water', 'gas', 'internet', 'fiber', 'comcast', 'att', 'verizon', 't-mobile',
    'insurance', 'geico', 'progressive', 'state farm',
    'mortgage', 'rent', 'carrington',
    'car payment', 'auto loan', 'ally',
    'affirm', 'klarna', 'afterpay',
]

found_subscriptions = []
found_bills = []
unknown = []

for r in recurring:
    name_lower = r.get('name', '').lower()
    display_lower = (r.get('display_name') or '').lower()
    combined = f"{name_lower} {display_lower}"
    
    matched = False
    for sub in known_subscriptions:
        if sub in combined:
            found_subscriptions.append(r)
            matched = True
            break
    
    if not matched:
        for bill in known_bills:
            if bill in combined:
                found_bills.append(r)
                matched = True
                break
    
    if not matched:
        unknown.append(r)

print(f"\n✅ Known Subscriptions Found: {len(found_subscriptions)}")
for r in found_subscriptions:
    print(f"   - {r.get('display_name') or r.get('name')}: ${abs(r.get('amount_mean', 0)):.2f}/{r.get('recurring_type', '?')}")

print(f"\n✅ Known Bills Found: {len(found_bills)}")
for r in found_bills:
    print(f"   - {r.get('display_name') or r.get('name')}: ${abs(r.get('amount_mean', 0)):.2f}/{r.get('recurring_type', '?')}")

print(f"\n❓ Other Recurring ({len(unknown)}):")
for r in unknown[:10]:
    print(f"   - {r.get('display_name') or r.get('name')}: ${abs(r.get('amount_mean', 0)):.2f}/{r.get('recurring_type', '?')}")
if len(unknown) > 10:
    print(f"   ... and {len(unknown) - 10} more")

# Calculate accuracy estimate
known_found = len(found_subscriptions) + len(found_bills)
print(f"\n{'─'*50}")
print(f"ACCURACY ESTIMATE")
print(f"{'─'*50}")
print(f"Known recurring patterns found: {known_found}")
print(f"Unknown/Other patterns: {len(unknown)}")
print(f"Total series: {len(recurring)}")
```

### 5.2 P2P Detection Accuracy

```python
import requests
from collections import Counter

p2p = requests.get("http://localhost:8000/api/p2p").json()

print("="*70)
print("P2P DETECTION ACCURACY CHECK")
print("="*70)

# Expected platforms
expected_platforms = ['zelle', 'venmo', 'cashapp', 'paypal', 'western_union', 'wire']

platforms_found = Counter(t.get('platform', 'unknown').lower() for t in p2p)

print(f"\nPlatform Detection:")
for platform in expected_platforms:
    count = platforms_found.get(platform, 0)
    status = "✅" if count > 0 else "⚠️"
    print(f"   {status} {platform}: {count} transactions")

# Check for false positives (spot check)
print(f"\nSpot Check - Sample P2P Transactions:")
import random
sample = random.sample(p2p, min(10, len(p2p)))

correct = 0
for t in sample:
    platform = t.get('platform', 'unknown')
    desc = t.get('description', 'N/A')[:50]
    amount = t.get('amount', 0)
    
    # Simple validation - does description contain platform name?
    is_valid = platform.lower() in desc.lower() or platform == 'wire'
    status = "✅" if is_valid else "⚠️"
    correct += 1 if is_valid else 0
    
    print(f"   {status} [{platform}] {desc} (${amount})")

print(f"\nSpot check accuracy: {correct}/{len(sample)} ({correct/len(sample)*100:.0f}%)")
```

---

## PHASE 6: GENERATE FINAL REPORT

### Create Comprehensive Report

```python
import requests
import json
from datetime import datetime

report = {
    'generated_at': datetime.now().isoformat(),
    'summary': {},
    'accounts': [],
    'detection_results': {},
    'accuracy': {},
    'issues': [],
    'recommendations': []
}

# Gather all data
stats = requests.get("http://localhost:8000/api/stats").json()
accounts = requests.get("http://localhost:8000/api/accounts").json()
recurring = requests.get("http://localhost:8000/api/recurring").json()
p2p = requests.get("http://localhost:8000/api/p2p").json()
transfers = requests.get("http://localhost:8000/api/transfers").json()
insights = requests.get("http://localhost:8000/api/insights/cards").json()

# Build report
report['summary'] = {
    'total_transactions': stats.get('total_transactions', 0),
    'total_accounts': len(accounts),
    'date_range': f"{stats.get('earliest_date', 'N/A')} to {stats.get('latest_date', 'N/A')}",
    'recurring_series': len(recurring),
    'p2p_transactions': len(p2p),
    'transfer_pairs': len(transfers) if isinstance(transfers, list) else 0,
    'insight_cards': len(insights)
}

report['accounts'] = accounts
report['detection_results'] = {
    'recurring': {
        'count': len(recurring),
        'monthly_total': sum(abs(r.get('amount_mean', 0)) for r in recurring if r.get('recurring_type') == 'monthly'),
        'series': recurring
    },
    'p2p': {
        'count': len(p2p),
        'by_platform': dict(Counter(t.get('platform') for t in p2p)),
        'transactions': p2p[:50]  # First 50
    },
    'transfers': {
        'count': len(transfers) if isinstance(transfers, list) else 0,
        'pairs': transfers[:20] if isinstance(transfers, list) else []
    }
}

# Save report
with open('docs/KASHAT_FINAL_VALIDATION_REPORT.json', 'w') as f:
    json.dump(report, f, indent=2, default=str)

print("Report saved to docs/KASHAT_FINAL_VALIDATION_REPORT.json")

# Also create markdown summary
md_report = f"""# KASHAT FINAL VALIDATION REPORT

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Transactions | {report['summary']['total_transactions']:,} |
| Accounts | {report['summary']['total_accounts']} |
| Date Range | {report['summary']['date_range']} |
| Recurring Series | {report['summary']['recurring_series']} |
| P2P Transactions | {report['summary']['p2p_transactions']} |
| Transfer Pairs | {report['summary']['transfer_pairs']} |
| Insight Cards | {report['summary']['insight_cards']} |

---

## Pipeline Execution

| Stage | Status | Count |
|-------|--------|-------|
| Import | ✅ | {report['summary']['total_transactions']} transactions |
| Transfer Detection | ✅ | {report['summary']['transfer_pairs']} pairs |
| P2P Detection | ✅ | {report['summary']['p2p_transactions']} transactions |
| Recurring Detection | ✅ | {report['summary']['recurring_series']} series |

---

## Recurring Series Detected

| Name | Amount | Cadence |
|------|--------|---------|
"""

for r in sorted(recurring, key=lambda x: abs(x.get('amount_mean', 0)), reverse=True)[:20]:
    name = r.get('display_name') or r.get('name', 'Unknown')
    amount = abs(r.get('amount_mean', 0))
    cadence = r.get('recurring_type', '?')
    md_report += f"| {name[:40]} | ${amount:.2f} | {cadence} |\n"

md_report += f"""
---

## P2P by Platform

| Platform | Count |
|----------|-------|
"""

p2p_platforms = Counter(t.get('platform') for t in p2p)
for platform, count in p2p_platforms.most_common():
    md_report += f"| {platform} | {count} |\n"

md_report += """
---

## Recommendations

1. Run AI categorization for full category coverage
2. Import additional accounts (savings) for transfer matching
3. Review low-confidence recurring series
4. Set up budget based on recurring costs

"""

with open('docs/KASHAT_FINAL_VALIDATION_REPORT.md', 'w') as f:
    f.write(md_report)

print("Markdown report saved to docs/KASHAT_FINAL_VALIDATION_REPORT.md")
```

---

## EXECUTION CHECKLIST

```
[ ] Phase 1: Data Clear
    [ ] Backup created
    [ ] All tables cleared
    [ ] Clean state verified

[ ] Phase 2: Import
    [ ] All statements imported
    [ ] No errors
    [ ] Counts recorded

[ ] Phase 3: Pipeline Verification
    [ ] Transfer detection ran
    [ ] P2P detection ran (all platforms)
    [ ] Recurring detection ran
    [ ] All detectors executed in order

[ ] Phase 4: Deep Analysis
    [ ] Account analysis complete
    [ ] Transfer analysis complete
    [ ] P2P analysis complete
    [ ] Recurring analysis complete
    [ ] Category distribution analyzed
    [ ] Income analyzed
    [ ] Spending patterns analyzed

[ ] Phase 5: Accuracy Assessment
    [ ] Recurring accuracy checked
    [ ] P2P accuracy checked
    [ ] Issues identified

[ ] Phase 6: Final Report
    [ ] JSON report generated
    [ ] Markdown report generated
    [ ] All findings documented
```

---

## SUCCESS CRITERIA

| Metric | Target | Actual |
|--------|--------|--------|
| Import Success | 100% | ___ |
| Pipeline Complete | All stages | ___ |
| Recurring Detected | 50+ series | ___ |
| P2P Detected | 100+ tx | ___ |
| Known Subscriptions Found | 80%+ | ___ |
| Known Bills Found | 80%+ | ___ |
| False Positives | <10% | ___ |

---

*Execute completely. Analyze deeply. Document everything.*
