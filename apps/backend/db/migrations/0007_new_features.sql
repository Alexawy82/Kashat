-- Migration 0007: New Features (Net Worth, Budget, Review)
-- Phase 5 of Kashat overhaul

-- ============================================================================
-- 5.1 Net Worth: Add account_type column
-- ============================================================================

ALTER TABLE account ADD COLUMN account_type TEXT DEFAULT 'checking';
-- Types: checking, savings, credit_card, loan, investment, asset

-- Update existing accounts based on name patterns
UPDATE account SET account_type =
    CASE
        WHEN lower(name) LIKE '%credit%' THEN 'credit_card'
        WHEN lower(name) LIKE '%saving%' THEN 'savings'
        WHEN lower(name) LIKE '%loan%' THEN 'loan'
        WHEN lower(name) LIKE '%mortgage%' THEN 'loan'
        WHEN lower(name) LIKE '%invest%' THEN 'investment'
        WHEN lower(name) LIKE '%brokerage%' THEN 'investment'
        WHEN lower(name) LIKE '%401k%' THEN 'investment'
        WHEN lower(name) LIKE '%ira%' THEN 'investment'
        ELSE 'checking'
    END
WHERE account_type IS NULL OR account_type = 'checking';

-- ============================================================================
-- 5.4 Budget System: Create budget tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS budget (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    period TEXT NOT NULL DEFAULT 'monthly',  -- monthly, weekly, yearly
    start_date TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budget_category (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    amount_limit REAL NOT NULL,
    rollover INTEGER DEFAULT 0,  -- Carry unused to next period
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (budget_id) REFERENCES budget(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS budget_period (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (budget_id) REFERENCES budget(id) ON DELETE CASCADE
);

-- Budget indexes
CREATE INDEX IF NOT EXISTS idx_budget_active ON budget(is_active);
CREATE INDEX IF NOT EXISTS idx_budget_category_budget ON budget_category(budget_id);
CREATE INDEX IF NOT EXISTS idx_budget_category_cat ON budget_category(category_id);
CREATE INDEX IF NOT EXISTS idx_budget_period_budget ON budget_period(budget_id);
CREATE INDEX IF NOT EXISTS idx_budget_period_dates ON budget_period(period_start, period_end);

-- ============================================================================
-- 5.5 Transaction Review: Add review columns
-- ============================================================================

ALTER TABLE [transaction] ADD COLUMN reviewed_at TEXT;
ALTER TABLE [transaction] ADD COLUMN reviewed_by TEXT;

-- Index for finding unreviewed transactions
CREATE INDEX IF NOT EXISTS idx_tx_reviewed ON [transaction](reviewed_at);

-- ============================================================================
-- Net Worth History: Create snapshots table for tracking over time
-- ============================================================================

CREATE TABLE IF NOT EXISTS networth_snapshot (
    id TEXT PRIMARY KEY,
    snapshot_date TEXT NOT NULL,
    total_assets REAL NOT NULL DEFAULT 0,
    total_liabilities REAL NOT NULL DEFAULT 0,
    net_worth REAL NOT NULL DEFAULT 0,
    breakdown_json TEXT,  -- JSON with by-account-type breakdown
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_networth_date ON networth_snapshot(snapshot_date);
