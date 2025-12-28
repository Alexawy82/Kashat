# Data Flow Diagrams

## Overview

This document describes the major data flows in LedgerLoop using Mermaid diagrams.

---

## 1. Transaction Import Flow

```mermaid
flowchart TD
    A[File Upload] --> B{File Type?}
    B -->|CSV| C[ingest_csv.py]
    B -->|PDF| D[ingest_pdf.py]

    C --> E[Parse Rows]
    D --> F{Bank Detection}
    F -->|Bank of America| G[boa_v2025.py]
    F -->|Other/Unknown| H[ai_parser.py]

    E --> I[normalize_description]
    G --> I
    H --> I

    I --> J[parse_amount]
    J --> K[parse_date]
    K --> L[Generate Fingerprint]

    L --> M{Duplicate Check}
    M -->|Exists| N[Skip/Log]
    M -->|New| O[Create Transaction]

    O --> P{AI Enabled?}
    P -->|Yes| Q[ingest_ai_workflow]
    P -->|No| R[Insert to DB]

    Q --> S[Merchant Normalization]
    S --> T[Category Suggestion]
    T --> U[Quality Scoring]
    U --> R

    R --> V[Update Import Stats]
    V --> W[Complete]
```

### Import Pipeline Details

| Step | Function | File | Output |
|------|----------|------|--------|
| 1. File Upload | POST /imports/csv | routes/imports.py | UploadFile |
| 2. Parse Rows | import_csv_upload() | ingest_csv.py | List[dict] |
| 3. Normalize | normalize_description() | normalization.py | Clean text |
| 4. Parse Amount | parse_amount() | normalization.py | Float |
| 5. Parse Date | parse_date() | normalization.py | ISO date |
| 6. Fingerprint | tx_fingerprint() | dedup.py | SHA1 hash |
| 7. Dedup Check | SELECT by fingerprint | db.py | Exists? |
| 8. AI Enhancement | process_import_run() | ai_import.py | Enhanced tx |
| 9. Insert | INSERT transaction | db.py | Transaction ID |

---

## 2. Categorization Flow

```mermaid
flowchart TD
    A[Transaction] --> B{Already Categorized?}
    B -->|Yes| C[Skip]
    B -->|No| D{Check Merchant Memory}

    D -->|Match Found| E[Apply Learned Category]
    D -->|No Match| F{Check Rules}

    F -->|Rule Matches| G[Apply Rule Category]
    F -->|No Rule| H{AI Enabled?}

    H -->|No| I[Mark Uncategorized]
    H -->|Yes| J[AI Categorization]

    J --> K{Confidence Level?}
    K -->|High >= 0.85| L[Auto-Apply + Learn]
    K -->|Medium 0.6-0.85| M[Suggest to User]
    K -->|Low < 0.6| N[Request User Input]

    L --> O[Update Merchant Memory]
    E --> P[Done]
    G --> P
    M --> P
    N --> P
    O --> P
```

### Categorization Priority

1. **Existing Category** - Already assigned, skip
2. **Merchant Memory** - Learned from previous corrections
3. **Rule Engine** - Regex-based pattern matching
4. **AI Categorization** - LLM-based inference
5. **Fallback** - Mark uncategorized for user review

---

## 3. AI Processing Flow

```mermaid
flowchart TD
    A[Request] --> B{Provider Selection}

    B -->|Auto Mode| C{LM Studio Available?}
    C -->|Yes| D[Use LM Studio]
    C -->|No| E{OpenAI Key?}
    E -->|Yes| F[Use OpenAI]
    E -->|No| G[Use Local Fallback]

    B -->|OpenAI| F
    B -->|LMStudio| D
    B -->|Local| G

    D --> H[Build Prompt]
    F --> H
    G --> I[Pattern Matching]

    H --> J[API Call with Retry]
    J --> K{Success?}
    K -->|No| L{Retries Left?}
    L -->|Yes| M[Exponential Backoff]
    M --> J
    L -->|No| G

    K -->|Yes| N[Parse JSON Response]
    N --> O{Valid JSON?}
    O -->|No| P[Regex Fallback]
    O -->|Yes| Q[Return Result]

    I --> Q
    P --> Q
```

### AI Provider Fallback Chain

| Priority | Provider | Latency | Cost |
|----------|----------|---------|------|
| 1 | LM Studio (local) | 100-500ms | Free |
| 2 | OpenAI (cloud) | 500-2000ms | Per token |
| 3 | Local Patterns | <10ms | Free |

---

## 4. Transfer Detection Flow

```mermaid
flowchart TD
    A[Transactions] --> B[Filter by Date Range]
    B --> C[Group by Amount Magnitude]

    C --> D{Same Amount?}
    D -->|No| E[Skip Pair]
    D -->|Yes| F{Opposite Signs?}

    F -->|No| E
    F -->|Yes| G{Same Account?}

    G -->|Yes| E
    G -->|No| H[Calculate Score]

    H --> I[Date Proximity Score]
    H --> J[Description Similarity]
    H --> K[Amount Tolerance]

    I --> L[Combine Scores]
    J --> L
    K --> L

    L --> M{Score >= Threshold?}
    M -->|No| E
    M -->|Yes| N{AI Enhancement?}

    N -->|Yes| O[AI Analyze Pair]
    N -->|No| P[Suggest Transfer]

    O --> Q{AI Confidence?}
    Q -->|High >= 0.9| R[Auto-Confirm]
    Q -->|Medium| P
    Q -->|Low| E

    P --> S[User Review]
    R --> T[Create match_transfer]
    S --> T
```

### Transfer Detection Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Amount Match | 40% | Same magnitude, opposite sign |
| Date Proximity | 30% | Within 3 days default |
| Description Similarity | 20% | Jaccard similarity |
| Account Diversity | 10% | Different accounts |

---

## 5. Recurring Detection Flow

```mermaid
flowchart TD
    A[All Transactions] --> B[Group by Merchant]
    B --> C{Min Occurrences >= 3?}

    C -->|No| D[Skip]
    C -->|Yes| E[Calculate Intervals]

    E --> F{Cadence Detection}
    F --> G[Weekly Pattern?]
    F --> H[Biweekly Pattern?]
    F --> I[Monthly Pattern?]
    F --> J[Quarterly Pattern?]
    F --> K[Annual Pattern?]

    G --> L[Validate Regularity]
    H --> L
    I --> L
    J --> L
    K --> L

    L --> M{Standard Deviation OK?}
    M -->|No| D
    M -->|Yes| N{LLM Classification?}

    N -->|Yes| O[Classify Type]
    N -->|No| P[Use Pattern Rules]

    O --> Q[subscription/bill/loan/etc]
    P --> Q

    Q --> R[Create recurring_series]
    R --> S[Link Transactions]
    S --> T[Calculate Metrics]

    T --> U[Annual Cost]
    T --> V[Next Payment Date]
    T --> W[Price Hike Detection]
```

### Recurring Type Classification

| Type | Pattern Examples |
|------|-----------------|
| subscription | Netflix, Spotify, Disney+, software SaaS |
| bill | Utility, internet, phone, rent |
| loan | Mortgage, auto loan, student loan, BNPL |
| credit_card | Credit card payments |
| insurance | Auto, home, life, health insurance |
| income | Payroll, salary, deposits |

---

## 6. P2P Detection Flow

```mermaid
flowchart TD
    A[Transaction Description] --> B{Pattern Detection}

    B --> C[Zelle Pattern?]
    B --> D[Venmo Pattern?]
    B --> E[CashApp Pattern?]
    B --> F[PayPal Pattern?]
    B --> G[Western Union?]

    C --> H[Extract Counterparty]
    D --> H
    E --> H
    F --> H
    G --> H

    H --> I[Normalize Name]
    I --> J{Direction Detection}

    J -->|Positive Amount| K[Received]
    J -->|Negative Amount| L[Sent]

    K --> M[Create p2p_transaction]
    L --> M

    M --> N{Counterparty Exists?}
    N -->|No| O[Create counterparty]
    N -->|Yes| P[Update Stats]

    O --> Q[Update Aggregates]
    P --> Q

    Q --> R{AI Enrichment?}
    R -->|Yes| S[Classify Type]
    R -->|No| T[Done]

    S --> U[person/business/unknown]
    U --> T
```

### P2P Provider Patterns

| Provider | Pattern Examples |
|----------|-----------------|
| Zelle | "ZELLE TO", "ZELLE FROM", "ZELLE PAYMENT" |
| Venmo | "VENMO", "VENMO CASHOUT" |
| CashApp | "CASH APP", "SQUARE CASH" |
| PayPal | "PAYPAL", "PP *" |
| Western Union | "WU", "WESTERN UNION" |

---

## 7. Analytics Calculation Flow

```mermaid
flowchart TD
    A[Request Analytics] --> B[Apply Filters]

    B --> C[Date Range]
    B --> D[Account ID]
    B --> E[Category ID]
    B --> F[Include Transfers?]

    C --> G[Query Transactions]
    D --> G
    E --> G
    F --> G

    G --> H{Exclude Adjustments}
    H --> I[Aggregate Totals]

    I --> J[Sum by Month]
    I --> K[Sum by Category]
    I --> L[Group by Merchant]

    J --> M[Monthly Summary]
    K --> N[Category Breakdown]
    L --> O[Top Merchants]

    M --> P{Include AI?}
    N --> P
    O --> P

    P -->|Yes| Q[AI Insights]
    P -->|No| R[Return Data]

    Q --> S[Spending Patterns]
    Q --> T[Anomaly Detection]
    Q --> U[Forecasts]

    S --> R
    T --> R
    U --> R
```

---

## 8. Rule Application Flow

```mermaid
flowchart TD
    A[New Transaction] --> B[Load Active Rules]
    B --> C[Sort by Priority]

    C --> D[For Each Rule]
    D --> E{Predicate Matches?}

    E -->|No| F[Next Rule]
    E -->|Yes| G[Apply Action]

    G --> H{Action Type}
    H -->|Set Category| I[Assign Category]
    H -->|Add Tag| J[Add Tag]
    H -->|Mark Business| K[Set is_business]

    I --> L{Continue Matching?}
    J --> L
    K --> L

    L -->|Yes| F
    L -->|No| M[Done]

    F --> N{More Rules?}
    N -->|Yes| D
    N -->|No| M
```

### Rule Predicate Types

| Type | Example | Description |
|------|---------|-------------|
| description_contains | "NETFLIX" | Substring match |
| description_regex | "AMZN.*MKTP" | Regex pattern |
| amount_gt | 100.00 | Amount greater than |
| amount_lt | 10.00 | Amount less than |
| merchant_is | "Starbucks" | Exact merchant match |

---

## 9. Export Flow

```mermaid
flowchart TD
    A[Export Request] --> B{Format}

    B -->|CSV| C[Build CSV Query]
    B -->|Parquet| D[Build Parquet Query]
    B -->|JSON| E[Build JSON Query]

    C --> F[Apply Filters]
    D --> F
    E --> F

    F --> G[Stream Results]

    G -->|CSV| H[Write CSV Headers]
    G -->|Parquet| I[Build Arrow Table]
    G -->|JSON| J[JSON Array]

    H --> K[Stream Rows]
    I --> L[Write Parquet File]
    J --> M[Return JSON]

    K --> N[Download Response]
    L --> N
    M --> N

    N --> O[Log Export Event]
```

---

## 10. Authentication Flow

```mermaid
flowchart TD
    A[Request] --> B{Has Token?}

    B -->|No| C{Protected Route?}
    C -->|No| D[Allow Request]
    C -->|Yes| E[401 Unauthorized]

    B -->|Yes| F[Validate JWT]
    F --> G{Valid?}

    G -->|No| E
    G -->|Yes| H{Expired?}

    H -->|Yes| I[401 Token Expired]
    H -->|No| J{Blacklisted?}

    J -->|Yes| E
    J -->|No| K[Extract User]

    K --> L{Admin Required?}
    L -->|No| D
    L -->|Yes| M{Is Admin?}

    M -->|No| N[403 Forbidden]
    M -->|Yes| D
```

---

*Generated by Claude Code Audit - December 27, 2025*
