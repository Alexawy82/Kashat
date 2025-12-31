# Kashat API Reference

Complete API documentation for the Kashat backend service.

**Base URL:** `http://localhost:8000/api`
**API Version:** 2.0.0
**Authentication:** JWT Bearer Token

---

## Table of Contents

- [Authentication](#authentication)
- [Transactions](#transactions)
- [Categories](#categories)
- [Rules](#rules)
- [Accounts](#accounts)
- [Imports](#imports)
- [Exports](#exports)
- [Transfers](#transfers)
- [Recurring](#recurring)
- [Analytics](#analytics)
- [Net Worth](#net-worth)
- [Budget](#budget)
- [Insights](#insights)
- [AI Features](#ai-features)
- [Admin](#admin)
- [Health](#health)
- [Error Responses](#error-responses)

---

## Authentication

All endpoints (except `/health`) require authentication via JWT bearer token.

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Using the Token

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## Transactions

### List Transactions

```http
GET /api/transactions
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Filter start date (YYYY-MM-DD) |
| `end_date` | string | Filter end date (YYYY-MM-DD) |
| `category` | string | Filter by category name |
| `account_id` | string | Filter by account |
| `search` | string | Search in description |
| `is_transfer` | boolean | Filter transfers |
| `is_recurring` | boolean | Filter recurring |
| `limit` | integer | Results per page (default: 50) |
| `offset` | integer | Pagination offset |

**Response:**
```json
{
  "items": [
    {
      "id": "tx_abc123",
      "date": "2024-01-15",
      "description": "AMAZON MARKETPLACE",
      "amount": -49.99,
      "category": "Shopping",
      "category_confidence": 0.95,
      "account_id": "checking",
      "merchant_clean": "Amazon",
      "is_transfer": false,
      "is_recurring": false,
      "flags": {
        "reviewed": true,
        "flagged": false
      }
    }
  ],
  "total": 1250,
  "limit": 50,
  "offset": 0
}
```

### Get Single Transaction

```http
GET /api/transactions/{id}
```

### Update Transaction Category

```http
POST /api/transactions/{id}/category
Content-Type: application/json

{
  "category": "Groceries"
}
```

### Update Transaction

```http
PATCH /api/transactions/{id}
Content-Type: application/json

{
  "reviewed": true,
  "flagged": false,
  "notes": "Business expense"
}
```

### Delete Transaction

```http
DELETE /api/transactions/{id}
```

### Bulk Update

```http
POST /api/transactions/bulk
Content-Type: application/json

{
  "ids": ["tx_1", "tx_2", "tx_3"],
  "action": "categorize",
  "category": "Groceries"
}
```

---

## Categories

### List Categories

```http
GET /api/categories
```

**Response:**
```json
{
  "categories": [
    {
      "id": "cat_1",
      "name": "Groceries",
      "parent": "Food & Dining",
      "icon": "shopping-cart",
      "color": "#4CAF50",
      "is_income": false,
      "transaction_count": 45
    }
  ]
}
```

### Create Category

```http
POST /api/categories
Content-Type: application/json

{
  "name": "Subscriptions",
  "parent": "Bills",
  "icon": "repeat",
  "color": "#2196F3"
}
```

### Update Category

```http
PUT /api/categories/{id}
Content-Type: application/json

{
  "name": "Monthly Subscriptions",
  "color": "#3F51B5"
}
```

### Delete Category

```http
DELETE /api/categories/{id}
```

---

## Rules

### List Rules

```http
GET /api/rules
```

**Response:**
```json
{
  "rules": [
    {
      "id": "rule_1",
      "name": "Amazon Shopping",
      "pattern": "AMAZON|AMZN",
      "pattern_type": "regex",
      "category": "Shopping",
      "priority": 10,
      "is_active": true,
      "match_count": 156
    }
  ]
}
```

### Create Rule

```http
POST /api/rules
Content-Type: application/json

{
  "name": "Netflix Subscription",
  "pattern": "NETFLIX",
  "pattern_type": "contains",
  "category": "Entertainment",
  "priority": 10
}
```

### Preview Rule Matches

```http
POST /api/rules/preview
Content-Type: application/json

{
  "pattern": "NETFLIX",
  "pattern_type": "contains"
}
```

**Response:**
```json
{
  "matches": [
    {
      "id": "tx_123",
      "description": "NETFLIX.COM",
      "amount": -15.99
    }
  ],
  "match_count": 12
}
```

### Apply Rule

```http
POST /api/rules/{id}/apply
```

---

## Accounts

### List Accounts

```http
GET /api/accounts
```

**Response:**
```json
{
  "accounts": [
    {
      "id": "checking",
      "name": "Main Checking",
      "type": "checking",
      "institution": "Bank of America",
      "balance": 5432.10,
      "transaction_count": 450,
      "last_import": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Account

```http
POST /api/accounts
Content-Type: application/json

{
  "id": "savings",
  "name": "Emergency Fund",
  "type": "savings",
  "institution": "Ally Bank"
}
```

### Update Account

```http
PUT /api/accounts/{id}
Content-Type: application/json

{
  "name": "Primary Checking"
}
```

---

## Imports

### Import CSV

```http
POST /api/imports/csv
Content-Type: multipart/form-data

file: <binary>
account_id: checking
```

**Response:**
```json
{
  "import_id": "imp_abc123",
  "status": "completed",
  "transactions_imported": 45,
  "duplicates_skipped": 3,
  "errors": []
}
```

### Import PDF (AI-Powered)

```http
POST /api/imports/pdf
Content-Type: multipart/form-data

file: <binary>
account_id: checking
bank_type: bank_of_america
```

### List Import Runs

```http
GET /api/imports/runs
```

### Get Import Details

```http
GET /api/imports/runs/{import_id}
```

### Parse Preview

```http
POST /api/imports/parse
Content-Type: multipart/form-data

file: <binary>
```

Returns parsed transactions without saving.

---

## Exports

### Export Transactions as CSV

```http
GET /api/export/transactions.csv
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date (YYYY-MM-DD) |
| `end_date` | string | End date (YYYY-MM-DD) |
| `category` | string | Filter by category |

### Export with Options

```http
POST /api/export
Content-Type: application/json

{
  "format": "csv",
  "include_transfers": false,
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

---

## Transfers

### Detect Transfers

```http
POST /api/transfers/suggest
```

**Response:**
```json
{
  "suggestions": [
    {
      "id": "sug_1",
      "from_transaction": "tx_123",
      "to_transaction": "tx_456",
      "amount": 500.00,
      "confidence": 0.95,
      "date_diff_days": 1
    }
  ]
}
```

### List Confirmed Transfers

```http
GET /api/transfers
```

### Confirm Transfer Pair

```http
POST /api/transfers/confirm
Content-Type: application/json

{
  "from_id": "tx_123",
  "to_id": "tx_456"
}
```

### Reject Suggested Transfer

```http
POST /api/transfers/reject
Content-Type: application/json

{
  "suggestion_id": "sug_1"
}
```

---

## Recurring

### Detect Recurring Transactions

```http
POST /api/recurring/suggest
```

**Response:**
```json
{
  "series": [
    {
      "id": "rec_1",
      "merchant": "Netflix",
      "amount": 15.99,
      "frequency": "monthly",
      "next_expected": "2024-02-15",
      "transaction_ids": ["tx_1", "tx_2", "tx_3"],
      "confidence": 0.98
    }
  ]
}
```

### List Recurring Series

```http
GET /api/recurring
```

### Confirm Series

```http
POST /api/recurring/confirm
Content-Type: application/json

{
  "series_id": "rec_1"
}
```

### Get Upcoming Bills

```http
GET /api/recurring/upcoming
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | Look-ahead days (default: 30) |

---

## Analytics

### Dashboard Summary

```http
GET /api/analytics/dashboard
```

**Response:**
```json
{
  "summary": {
    "income": 5200.00,
    "spending": 3800.00,
    "net": 1400.00,
    "savings_rate": 26.92
  },
  "spending_by_category": [
    {"category": "Housing", "amount": 1500.00, "percent": 39.47},
    {"category": "Food", "amount": 600.00, "percent": 15.79}
  ],
  "recent_transactions": [...]
}
```

### Monthly Summary

```http
GET /api/analytics/monthly
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `months` | integer | Number of months (default: 12) |

### Category Breakdown

```http
GET /api/analytics/category-monthly
```

### Top Merchants

```http
GET /api/analytics/merchants
```

### Cash Flow

```http
GET /api/analytics/cashflow
```

### Financial Health Score

```http
GET /api/analytics/health
```

**Response:**
```json
{
  "health_report": {
    "overall_score": 78,
    "health_grade": "B+",
    "component_scores": {
      "savings_rate": 85,
      "debt_to_income": 70,
      "expense_stability": 80,
      "emergency_fund": 65
    },
    "key_strengths": [
      "Consistent savings habit",
      "Low credit utilization"
    ],
    "improvement_areas": [
      "Build emergency fund",
      "Reduce dining out expenses"
    ],
    "recommendations": [...]
  }
}
```

---

## Net Worth

### Get Complete Net Worth

```http
GET /api/networth/complete
```

**Response:**
```json
{
  "net_worth": 125000.00,
  "total_assets": 175000.00,
  "total_liabilities": 50000.00,
  "bank_accounts": 25000.00,
  "assets": [...],
  "liabilities": [...],
  "asset_breakdown": {
    "checking": 15000,
    "savings": 10000,
    "investment": 50000,
    "real_estate": 100000
  },
  "liability_breakdown": {
    "mortgage": 45000,
    "credit_card": 5000
  }
}
```

### Add Asset

```http
POST /api/networth/assets
Content-Type: application/json

{
  "name": "Investment Account",
  "asset_type": "investment",
  "current_value": 50000.00,
  "institution": "Vanguard"
}
```

### Add Liability

```http
POST /api/networth/liabilities
Content-Type: application/json

{
  "name": "Car Loan",
  "liability_type": "auto_loan",
  "current_balance": 15000.00,
  "interest_rate": 4.5,
  "minimum_payment": 350.00
}
```

---

## Budget

### Get Budgets

```http
GET /api/budgets
```

### Create Budget

```http
POST /api/budgets
Content-Type: application/json

{
  "category": "Groceries",
  "amount": 500.00,
  "period": "monthly"
}
```

### Get Budget Status

```http
GET /api/budgets/status
```

**Response:**
```json
{
  "budgets": [
    {
      "category": "Groceries",
      "budgeted": 500.00,
      "spent": 375.00,
      "remaining": 125.00,
      "percent_used": 75.0,
      "on_track": true
    }
  ],
  "total_budgeted": 2500.00,
  "total_spent": 1875.00
}
```

---

## Insights

### Get Smart Insights

```http
GET /api/insights
```

**Response:**
```json
{
  "insights": [
    {
      "type": "spending_spike",
      "title": "Unusual spending detected",
      "description": "Your dining expenses are 45% higher than usual this month",
      "severity": "warning",
      "category": "Food & Dining",
      "amount_diff": 150.00
    },
    {
      "type": "subscription_increase",
      "title": "Price increase detected",
      "description": "Netflix increased from $15.99 to $17.99",
      "severity": "info",
      "merchant": "Netflix"
    }
  ]
}
```

---

## AI Features

### AI Categorize Transaction

```http
POST /api/ai/categorize
Content-Type: application/json

{
  "description": "WHOLEFDS MKT 10234",
  "amount": -87.50
}
```

**Response:**
```json
{
  "category": "Groceries",
  "confidence": 0.94,
  "merchant_clean": "Whole Foods Market",
  "alternatives": [
    {"category": "Food & Dining", "confidence": 0.65}
  ]
}
```

### AI Batch Categorize

```http
POST /api/ai/categorize/batch
Content-Type: application/json

{
  "transaction_ids": ["tx_1", "tx_2", "tx_3"]
}
```

### AI Merchant Enrichment

```http
POST /api/ai/enrich
Content-Type: application/json

{
  "description": "AMZN MKTP US*2H4K9"
}
```

**Response:**
```json
{
  "merchant_clean": "Amazon",
  "merchant_category": "Online Shopping",
  "is_subscription": false
}
```

---

## Admin

### Backup Database

```http
POST /api/admin/backup
Authorization: Bearer <admin_token>
```

### Restore Database

```http
POST /api/admin/restore
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

file: <backup_file>
```

### Get Audit Logs

```http
GET /api/audit/logs
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | Filter by action type |
| `limit` | integer | Results per page |

---

## Health

### Basic Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

### Liveness Probe

```http
GET /api/health/live
```

### Readiness Probe

```http
GET /api/health/ready
```

### Full Health Check

```http
GET /api/health/full
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": {
    "status": "connected",
    "transaction_count": 1250
  },
  "ai": {
    "provider": "lmstudio",
    "status": "available"
  },
  "uptime_seconds": 86400
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message description",
  "error_code": "VALIDATION_ERROR",
  "field": "amount"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Invalid or missing token |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `409` | Conflict - Resource already exists |
| `422` | Validation Error - Invalid data |
| `429` | Too Many Requests - Rate limited |
| `500` | Internal Server Error |

### Rate Limiting

When rate limited, response includes:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "detail": "Rate limit exceeded: 100/minute"
}
```

---

## Interactive API Documentation

Access the interactive Swagger UI at:

```
http://localhost:8000/docs
```

---

[Back to README](../README.md) | [Quick Start](QUICKSTART.md) | [Deployment](DEPLOYMENT.md)
