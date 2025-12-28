# LedgerLoop User Guide

Welcome to LedgerLoop! This guide will help you get started with managing your personal finances.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Importing Transactions](#importing-transactions)
3. [Managing Transactions](#managing-transactions)
4. [Categories and Rules](#categories-and-rules)
5. [Transfers](#transfers)
6. [Recurring Transactions](#recurring-transactions)
7. [Analytics and Reports](#analytics-and-reports)
8. [AI Features](#ai-features)
9. [Data Management](#data-management)
10. [Settings](#settings)

---

## Getting Started

### First Login

1. Open your browser and navigate to `http://localhost:3000`
2. Log in with default credentials:
   - Username: `admin`
   - Password: `adminadmin`
3. **Important**: Change your password after first login via Settings > Security

### Dashboard Overview

The dashboard provides a quick overview of your finances:
- **Monthly Summary**: Income vs. expenses for the current month
- **Category Breakdown**: Spending by category
- **Recent Transactions**: Latest activity
- **Quick Actions**: Common tasks like import and export

---

## Importing Transactions

### CSV Import

1. Navigate to **Settings > Data Management**
2. Click **Bulk Upload**
3. Select one or more CSV files from your bank
4. Review the import summary
5. Confirm to import transactions

Supported CSV formats:
- Bank of America statements
- Generic CSV with columns: date, description, amount

### PDF Import

1. Navigate to **Settings > Data Management**
2. Click **Bulk Upload**
3. Select PDF bank statements
4. The system will extract transactions automatically

Currently supported:
- Bank of America eStatements

### Import Runs

Each upload creates an "Import Run" that tracks:
- Files uploaded
- Transactions imported
- Any errors or duplicates skipped

View and manage import runs in **Settings > Data Management**.

---

## Managing Transactions

### Viewing Transactions

Navigate to **Transactions** to see all your transactions.

**Filtering Options:**
- Date range
- Category (including uncategorized)
- Amount range
- Search by description
- Account filter

### Editing Transactions

Click on any transaction to:
- Change category
- Edit description/notes
- Mark as transfer
- Flag for review

### Bulk Operations

1. Select multiple transactions using checkboxes
2. Use bulk actions:
   - **Set Category**: Apply category to all selected
   - **Create Rule**: Create rule from selected pattern
   - **Mark as Transfer**: Link related transactions

---

## Categories and Rules

### Managing Categories

Navigate to **Categories** to:
- View all categories in a hierarchical tree
- Create new categories and subcategories
- Edit or delete existing categories
- See transaction counts per category

### Creating Rules

Rules automatically categorize transactions based on patterns.

**Create a Rule:**
1. Go to **Rules** page
2. Click **Create Rule**
3. Define conditions:
   - Description pattern (regex supported)
   - Amount range (min/max)
   - Date range
4. Set action (assign category)
5. Set priority (lower = higher priority)

**Apply Rules:**
- Rules are applied automatically to new imports
- Use **Apply All Rules** to re-categorize existing transactions
- Preview before applying to see affected transactions

---

## Transfers

Internal transfers between your accounts are automatically detected.

### P2P Cashouts (Zelle / Venmo / Cash App / Western Union)

LedgerLoop also detects P2P-style transfers that are *not* internal account-to-account moves (cashouts/payments to others).

- Go to **Transfers** page
- In **P2P Cashouts**, click **Refresh P2P scan**
- Expand a row to see the underlying transactions (direction, amount, description)
- If a provider doesn’t include the recipient in the statement (common for Western Union), set it manually in the expanded list so future summaries group correctly

### Detecting Transfers

1. Go to **Transfers** page
2. Click **Suggest Transfers**
3. Review pending matches
4. Approve or reject each suggestion

### Transfer Settings

- **Amount Tolerance**: How close amounts must match (default: $0.01)
- **Date Range**: Maximum days apart for a transfer pair (default: 3 days)

### Managing Transfers

**Confirmed Transfers:**
- View all linked transfer pairs
- Toggle "Include in Analytics" to exclude from spending reports
- Unlink if incorrectly matched

---

## Recurring Transactions

LedgerLoop automatically detects subscriptions and recurring payments.

### Detecting Recurring

1. Go to **Recurring** page
2. Click **Suggest Recurring**
3. Review detected patterns
4. Approve valid series

### Recurring Features

- **Confidence Score**: How certain the detection is
- **Frequency**: Monthly cadence is prioritized for subscriptions/bills
- **Next Expected**: Predicted next occurrence
- **Monthly Cost**: Calculated recurring expense

### Managing Subscriptions

- View all confirmed recurring series
- Track monthly subscription spend
- See upcoming payments
- Cancel tracking for ended subscriptions

### Home Utilities

Utilities often have variable amounts. LedgerLoop tracks them as recurring series (when cadence is consistent) and shows them separately from app/streaming subscriptions.

---

## Analytics and Reports

### Dashboard Analytics

The main dashboard shows:
- Monthly income vs. expenses trend
- Category breakdown pie chart
- Top merchants by spending
- Cash flow analysis

### Detailed Reports

Navigate to **Analytics** (via dashboard) for:
- Custom date range analysis
- Month-over-month comparisons
- Category deep dives
- Merchant spending patterns

### Exporting Data

1. Go to **Settings > Data Management** or use the Export button
2. Choose format:
   - **CSV**: Standard spreadsheet format
   - **Parquet**: Optimized for large datasets
3. Apply filters (optional)
4. Download your data

---

## AI Features

LedgerLoop includes optional AI-powered features for smart categorization.

### Smart Categorization

AI can suggest categories for uncategorized transactions:
1. Go to **AI** page
2. Click **Enhance Uncategorized**
3. Set confidence threshold
4. Review and apply suggestions

### AI Settings

Configure AI in **Settings**:
- **Provider**: LMStudio (local) or OpenAI (cloud)
- **Model**: Choose appropriate model for your setup
- **Confidence Threshold**: Minimum confidence to auto-apply

### Local AI (Recommended)

For privacy, use local AI with LMStudio:
1. Install [LMStudio](https://lmstudio.ai)
2. Download a model (recommended: Qwen 3 4B)
3. Start the local server
4. Configure LedgerLoop to use `http://localhost:1234/v1`

---

## Data Management

### Import Runs

View all import runs in **Settings > Data Management**:
- **Files**: See all files in each run
- **Summary**: Monthly transaction counts
- **Reprocess**: Re-import with updated rules
- **Delete**: Remove all transactions from a run

### Backup & Restore

Your data is stored locally in `~/.ledgerloop/ledgerloop.duckdb`

**Backup:**
```bash
cp ~/.ledgerloop/ledgerloop.duckdb ~/.ledgerloop/backup_$(date +%Y%m%d).duckdb
```

**Restore:**
```bash
cp ~/.ledgerloop/backup_YYYYMMDD.duckdb ~/.ledgerloop/ledgerloop.duckdb
```

### Database Location

- Default: `~/.ledgerloop/`
- Custom: Set `LEDGERLOOP_DATA_DIR` environment variable

---

## Settings

### Security

- **Change Password**: Update your login credentials
- **Session Management**: View active sessions

### Display

- **Theme**: Light/Dark mode
- **Date Format**: MM/DD/YYYY or DD/MM/YYYY
- **Currency**: Display currency symbol

### AI Configuration

- **Enable AI**: Toggle AI features
- **Provider**: Local (LMStudio) or Cloud (OpenAI)
- **Model**: Select AI model
- **Auto-categorize**: Automatically apply high-confidence suggestions

---

## Tips & Best Practices

### Getting Accurate Data

1. **Import all accounts**: Include checking, savings, and credit cards
2. **Run transfer detection**: Link internal transfers to avoid double-counting
3. **Create rules**: Automate categorization for recurring merchants
4. **Review regularly**: Check uncategorized transactions weekly

### Improving Categorization

1. Start with rules for your top merchants
2. Use AI suggestions for one-off transactions
3. Create broad rules (e.g., "amazon" matches all Amazon purchases)
4. Use category hierarchy for detailed tracking

### Privacy

- All data stays on your machine
- No cloud sync or external services
- Database is a single file you control
- Encrypted backups recommended for sensitive data

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `j/k` | Navigate up/down in lists |
| `Space` | Toggle selection |
| `Enter` | Open selected item |
| `c` | Open category picker |
| `r` | Create rule from selection |
| `Escape` | Close modal/cancel |

---

## Getting Help

- **Documentation**: Check the `/docs` folder
- **API Reference**: Visit `/api/docs` for Swagger UI
- **Issues**: Report bugs at GitHub repository
- **Logs**: Check `~/.ledgerloop/logs/` for troubleshooting

---

*LedgerLoop - Your finances, your control.*
