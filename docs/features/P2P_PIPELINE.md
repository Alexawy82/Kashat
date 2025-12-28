# P2P Detection Pipeline

## Overview

The P2P (Person-to-Person) Detection Pipeline identifies transactions between you and real people or personal transfers, distinguishing them from business subscriptions, fees, and autopay transactions.

## Design Philosophy

**Single Responsibility**: The P2P pipeline focuses solely on detecting and enriching person-to-person transfers. Recurring pattern detection is handled by the separate Recurring Pipeline.

This separation avoids duplication and ensures each system does one thing well:
- **P2P Pipeline**: Who you transact with (counterparties)
- **Recurring Pipeline**: What happens regularly (patterns/subscriptions)

## Supported Services

| Service | Detection Method | Counterparty Extraction |
|---------|------------------|-------------------------|
| Zelle | `ZELLE`, `ZEL` patterns | Name after PAYMENT TO/FROM |
| Venmo | `VENMO` pattern | Name after PAYMENT/CASHOUT |
| CashApp | `CASH APP`, `SQUARE CASH` | Name in description |
| PayPal | `PAYPAL` (P2P only) | INST XFER patterns |
| Western Union | `WESTERN UNION` | Manual or AI extraction |
| Wire Transfer | `WIRE`, `FED` patterns | Reference/beneficiary |

## Multi-Layer Filtering

The pipeline applies multiple filters to ensure only genuine P2P transfers are captured:

### Filter 1: Internal Transfers
Skip transactions already matched as internal account-to-account transfers.

### Filter 2: Fee Transactions
Skip service fees that aren't actual transfers:
```python
FEE_PATTERNS = [
    r"\bfee\b",
    r"\bservice\s*charge\b",
    r"\btransaction\s*fee\b",
    r"\bmonthly\s*fee\b",
    r"\binterest\b",
    # ... more patterns
]
```

### Filter 3: Autopay/Bill Pay
Skip automated payments to businesses:
```python
AUTOPAY_PATTERNS = [
    r"\bautopay\b",
    r"\bciti\s+autopay\b",
    r"\brocket\s+money\b",
    r"\balbert\s+genius\b",
    r"\bgoogle\s+store\s+des:payment\b",
    r"\bedi\s+pymnts?\b",
    r"\bbill\s*pay\b",
    # ... more patterns
]
```

### Filter 4: Invalid Counterparties
Skip transactions where no valid person/entity name can be extracted:
- "PAYMENT"
- "TRANSFER"
- "UNKNOWN"
- Single characters
- Pure numbers

### Filter 5: PayPal Business Transactions
PayPal transactions to known businesses are filtered out:
```python
if service == "paypal" and counterparty_type == "business":
    return None  # Skip - belongs in recurring, not P2P
```

## Known Businesses List

Transactions to these entities are classified as business (not P2P):
- **Streaming**: Netflix, Spotify, Disney, Apple Music, YouTube
- **Gaming**: PlayStation, Xbox, Epic Games, iRacing, Fanatec
- **Software**: Adobe, Microsoft, OpenAI, GitHub, Notion
- **Services**: Amazon Prime, Uber, Lyft, DoorDash
- **VPN/Security**: NordVPN, ExpressVPN, PrivateInternet
- **Web Services**: GoDaddy, Cloudflare, Namecheap, DigitalOcean

## Counterparty Management

### Fuzzy Name Matching
Names are normalized and fuzzy-matched to group variations:
- "MAI MEDHAT", "Mai Medhat", "MAI M" → Single counterparty

### Type Classification
Counterparties are classified as:
- **Person**: Names with spaces, mixed case
- **Business**: ALL CAPS without spaces, known business patterns

### Merge Capability
Duplicate counterparties can be merged via the UI, consolidating:
- Transaction history
- Total amounts sent/received
- Aliases list

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/p2p/detect` | Run P2P detection (with optional AI) |
| POST | `/api/p2p/enrich` | Enrich unclassified counterparties with AI |
| GET | `/api/p2p/stats` | Get P2P summary statistics |
| GET | `/api/p2p/counterparties` | List all counterparties |
| GET | `/api/p2p/counterparties/{id}/transactions` | Get transactions for counterparty |
| POST | `/api/p2p/merge-counterparties` | Merge two counterparties |
| GET | `/api/p2p/enrichment-stats` | Get enrichment status |

## Pipeline Flow

```
Transaction
    │
    ├── Is internal transfer? ──────────── Skip
    │
    ├── Is fee transaction? ────────────── Skip
    │
    ├── Is autopay/bill pay? ───────────── Skip
    │
    ├── Can extract counterparty? ──────── No → Skip
    │
    ├── Is PayPal + Business? ──────────── Skip (→ Recurring Pipeline)
    │
    └── Valid P2P ─────────────────────────────
            │
            ├── Normalize counterparty name
            │
            ├── Fuzzy match to existing counterparty
            │
            ├── Create or update counterparty record
            │
            └── Link transaction to counterparty
```

## Frontend Integration

### People & Transfers Page (`/transfers`)

**Tabs**:
1. **People** (default): Shows all counterparties with filters
2. **Internal Transfers**: Existing transfer matching functionality

**Actions**:
- **Analyze P2P**: Runs detect + enrich pipeline
- **Quick Detect**: Fast rule-based detection only
- **AI Detect**: Full AI-powered detection
- **Enrich Only**: AI enrichment for unclassified counterparties

**Counterparty Card**:
- Name and type (Person/Business)
- Service icons
- Total sent/received
- Transaction count
- Recurring indicator (if applicable)

**Detail Sheet** (on click):
- Full profile with aliases
- Statistics (totals, first/last dates)
- Action buttons (Merge, Link to Recurring)
- Recent transactions list

## Data Model

### p2p_transaction Table
```sql
CREATE TABLE p2p_transaction (
    id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR REFERENCES transaction(id),
    counterparty_id VARCHAR REFERENCES counterparty(id),
    provider VARCHAR,           -- zelle, venmo, cashapp, paypal, wire, wu
    direction VARCHAR,          -- sent, received
    amount DECIMAL,
    detected_at TIMESTAMP,
    ai_enriched BOOLEAN DEFAULT FALSE
)
```

### counterparty Table
```sql
CREATE TABLE counterparty (
    id VARCHAR PRIMARY KEY,
    name VARCHAR,               -- Normalized canonical name
    normalized_name VARCHAR,    -- Lowercase for matching
    type VARCHAR,               -- person, business
    aliases TEXT,               -- JSON array of alternate names
    total_sent DECIMAL,
    total_received DECIMAL,
    transaction_count INTEGER,
    first_seen DATE,
    last_seen DATE,
    is_recurring BOOLEAN DEFAULT FALSE
)
```

## Performance

- Detection processes ~5,000 transactions in <5 seconds
- AI enrichment batches 50 counterparties per request
- Fuzzy matching uses normalized name index for O(1) lookups

## Future Enhancements

1. **Smart Grouping**: Auto-suggest counterparty merges based on similarity
2. **Payment Scheduling**: Predict next payment dates for recurring P2P
3. **Network Graph**: Visualize your payment network
4. **Balance Tracking**: Track who owes whom across multiple transactions
