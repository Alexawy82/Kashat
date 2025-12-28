# Changelog

All notable changes to Kashat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-27

### Added

#### New Features
- **Net Worth Tracking**: Calculate and display total assets vs liabilities across all accounts
  - Account type classification (checking, savings, credit_card, loan, investment, asset)
  - Net worth history with monthly snapshots
  - Breakdown by account type

- **Bill Calendar**: Visual calendar for upcoming payments
  - Monthly calendar view with bills on due dates
  - 7/30/90 day upcoming bill summaries
  - Overdue bill alerts
  - Today's bills widget

- **Budget System**: Category-based spending limits
  - Create budgets with period (monthly/weekly/yearly)
  - Set limits per category
  - Rollover support for unused amounts
  - Progress tracking with visual indicators

- **Smart Insight Cards**: Dashboard intelligence widgets
  - Spending spike detection (category spending above average)
  - Price increase alerts for recurring payments
  - Unused subscription detection
  - Top spending categories summary

- **Transaction Review**: Mark transactions as reviewed
  - Single transaction review endpoint
  - Bulk review for multiple transactions
  - Unreviewed transaction listing
  - Review timestamp and reviewer tracking

#### New API Endpoints
- `GET /api/networth` - Calculate current net worth
- `GET /api/networth/history` - Historical net worth data
- `POST /api/networth/snapshot` - Create net worth snapshot
- `GET /api/networth/snapshots` - List stored snapshots
- `GET /api/calendar/upcoming` - Upcoming bills
- `GET /api/calendar/month/{year}/{month}` - Monthly calendar
- `GET /api/calendar/summary` - Bill summary (7/30/90 days)
- `GET /api/calendar/today` - Today's bills
- `GET /api/calendar/overdue` - Overdue bills
- `GET /api/budgets` - List budgets
- `POST /api/budgets` - Create budget
- `GET /api/budgets/{id}` - Get budget details
- `PUT /api/budgets/{id}` - Update budget
- `DELETE /api/budgets/{id}` - Delete budget
- `GET /api/budgets/{id}/progress` - Budget progress
- `PUT /api/budgets/{id}/categories/{cat_id}` - Set category limit
- `DELETE /api/budgets/{id}/categories/{cat_id}` - Remove category limit
- `GET /api/insights/cards` - Smart insight cards
- `GET /api/insights/spending-spikes` - Spending spike analysis
- `GET /api/insights/price-increases` - Price increase detection
- `GET /api/insights/unused-subscriptions` - Unused subscription detection
- `GET /api/insights/top-categories` - Top spending categories
- `POST /api/transactions/{id}/review` - Mark transaction reviewed
- `POST /api/transactions/bulk/review` - Bulk review transactions
- `GET /api/transactions/unreviewed/list` - List unreviewed transactions

#### Frontend Pages
- `/calendar` - Bill calendar page with monthly view
- `/budget` - Budget management page with progress tracking

#### Dashboard Widgets
- `NetWorthCard` - Asset/liability overview
- `BudgetSummaryCard` - Quick budget status
- `UpcomingBillsCard` - Next 7 days bills

### Changed

- **Renamed from LedgerLoop to Kashat**
  - Package renamed to `kashat`
  - Environment variables use `KASHAT_` prefix (with `LEDGERLOOP_` backwards compatibility)
  - UI branding updated throughout

- **Database Schema**
  - Added `account_type` column to `account` table
  - Added `reviewed_at` and `reviewed_by` columns to `transaction` table
  - Added `budget`, `budget_category`, `budget_period` tables
  - Added `networth_snapshot` table
  - Added `account_id` column to `recurring_series` table
  - Added performance indexes for common queries

- **Navigation**
  - Added Calendar and Budget to main navigation
  - Reorganized dashboard with new widget grid

- **API Route Ordering**
  - Fixed bulk routes to come before parameterized routes to prevent path conflicts

### Fixed

- Fixed route matching issue where `/bulk/review` was matched by `/{tx_id}/review`
- Fixed SQL syntax for reserved word `transaction` (now uses `[transaction]`)
- Fixed environment variable compatibility for test isolation
- Added missing `account_id` column to `recurring_series` for calendar queries

### Tests

- Added 35 new feature tests covering:
  - Net Worth API (5 tests)
  - Calendar API (7 tests)
  - Budget API (10 tests)
  - Insights API (8 tests)
  - Integration workflows (5 tests)

---

## [1.0.0] - 2025-12-01

### Initial Release

- Multi-format import (CSV, PDF)
- Smart deduplication
- AI-powered categorization
- Transfer detection
- Recurring payment detection
- P2P transaction detection
- Analytics dashboard
- Rule engine
- Merchant memory
