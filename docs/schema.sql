-- LedgerLoop Database Schema
-- Database: DuckDB (SQLite-compatible)
-- Version: 1.0 with AI enhancements

-- Enable object cache for performance
PRAGMA enable_object_cache;

-- Core Entity Tables

-- Financial institutions (banks, credit unions, etc.)
CREATE TABLE IF NOT EXISTS institution (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

-- User accounts within institutions
CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    institution_id TEXT,
    name TEXT NOT NULL,
    type TEXT,                -- checking, savings, credit, investment
    last4 TEXT,               -- last 4 digits for identification
    currency TEXT,            -- USD, EUR, etc.
    FOREIGN KEY (institution_id) REFERENCES institution(id)
);

-- Import Tracking Tables

-- Each import session (user uploads files)
CREATE TABLE IF NOT EXISTS import_run (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    source TEXT,              -- web_upload, cli, api
    user_note TEXT,
    
    -- AI Enhancement tracking
    ai_enhanced_count INTEGER DEFAULT 0,
    ai_avg_quality_score FLOAT DEFAULT 0.0,
    ai_anomalies_detected INTEGER DEFAULT 0,
    ai_analysis_complete BOOLEAN DEFAULT FALSE,
    ai_suggested_rules_count INTEGER DEFAULT 0,
    ai_workflow_id TEXT
);

-- Files uploaded in each import run
CREATE TABLE IF NOT EXISTS import_file (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    path TEXT,                -- original filename/path
    hash TEXT,                -- file content hash for deduplication
    type TEXT,                -- csv, pdf, qfx, etc.
    FOREIGN KEY (run_id) REFERENCES import_run(id)
);

-- Raw parsed records before normalization (for audit/debugging)
CREATE TABLE IF NOT EXISTS raw_record (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    row_no INTEGER NOT NULL,  -- line number in original file
    raw_json TEXT NOT NULL,   -- original parsed data as JSON
    parsed_at TIMESTAMP NOT NULL,
    FOREIGN KEY (file_id) REFERENCES import_file(id)
);

-- Core Transaction Table

-- Normalized financial transactions
CREATE TABLE IF NOT EXISTS transaction (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    posted_at DATE NOT NULL,         -- transaction date
    amount DOUBLE NOT NULL,          -- positive = income, negative = expense
    currency TEXT,
    description_norm TEXT NOT NULL,  -- normalized description
    external_id TEXT,                -- bank's transaction ID
    fingerprint TEXT NOT NULL,       -- deduplication fingerprint
    source_raw_id TEXT,              -- link to raw_record
    
    -- Classification flags
    is_business BOOLEAN NOT NULL DEFAULT FALSE,
    is_income BOOLEAN NOT NULL DEFAULT FALSE,
    is_adjustment BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Special transaction types
    zelle_direction TEXT,            -- sent, received
    zelle_counterparty TEXT,         -- Zelle recipient/sender
    p2p_provider TEXT,               -- zelle, venmo, cashapp, western_union
    p2p_direction TEXT,              -- to, from, unknown
    p2p_counterparty TEXT,           -- best-effort; may require manual override (e.g., Western Union)
    payee_alias TEXT,                -- user-defined payee name
    
    -- AI Enhancement fields
    ai_merchant_name TEXT,           -- AI-extracted merchant name
    ai_category_suggestions TEXT,    -- JSON array of suggested categories
    ai_confidence_score FLOAT,       -- AI confidence (0.0-1.0)
    ai_processed_at TIMESTAMP,       -- when AI processed this transaction
    ai_provider TEXT,                -- openai, local, heuristic
    ai_model TEXT,                   -- gpt-4, llama-2, etc.
    ai_latency_ms INTEGER,           -- AI processing time
    
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transaction(account_id, posted_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tx_fingerprint ON transaction(fingerprint);

-- Category Management

-- Hierarchical category system
CREATE TABLE IF NOT EXISTS category (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT,           -- for hierarchical categories
    FOREIGN KEY (parent_id) REFERENCES category(id)
);

-- Transaction-Category relationships (many-to-many)
CREATE TABLE IF NOT EXISTS transaction_category (
    tx_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    applied_by TEXT,          -- rule_id, ai_provider, user
    PRIMARY KEY (tx_id, category_id),
    FOREIGN KEY (tx_id) REFERENCES transaction(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- Simple tagging system
CREATE TABLE IF NOT EXISTS transaction_tag (
    tx_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (tx_id, tag),
    FOREIGN KEY (tx_id) REFERENCES transaction(id) ON DELETE CASCADE
);

-- Rules Engine

-- Classification rules (predicate -> action)
CREATE TABLE IF NOT EXISTS rule (
    id TEXT PRIMARY KEY,
    priority INTEGER NOT NULL,        -- execution order (lower = higher priority)
    predicate_json TEXT NOT NULL,     -- condition as JSON
    action_json TEXT NOT NULL,        -- action as JSON
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- Transfer Detection

-- Detected transfer pairs between accounts
CREATE TABLE IF NOT EXISTS match_transfer (
    left_tx_id TEXT NOT NULL,
    right_tx_id TEXT NOT NULL,
    group_id TEXT,                    -- for multi-way transfers
    score DOUBLE,                     -- confidence score
    method TEXT,                      -- detection algorithm used
    decided_at TIMESTAMP,             -- when user confirmed/rejected
    include_in_analytics BOOLEAN DEFAULT FALSE,  -- exclude from spending analysis
    PRIMARY KEY (left_tx_id, right_tx_id),
    FOREIGN KEY (left_tx_id) REFERENCES transaction(id),
    FOREIGN KEY (right_tx_id) REFERENCES transaction(id)
);

-- Recurring Transaction Analysis

-- Detected recurring payment series
CREATE TABLE IF NOT EXISTS recurring_series (
    id TEXT PRIMARY KEY,
    name TEXT,                        -- user-friendly name
    cadence TEXT,                     -- monthly, weekly, etc.
    anchor_day INTEGER,               -- day of month/week
    amount_mean DOUBLE,               -- average amount
    amount_sd DOUBLE,                 -- standard deviation
    rule_ref TEXT,                    -- associated rule ID
    last_date DATE,                   -- last seen transaction
    next_date DATE,                   -- predicted next transaction
    price_hike BOOLEAN,               -- detected price increase
    status TEXT,                      -- active, paused, cancelled
    decided_at TIMESTAMP              -- when user reviewed
);

-- Transaction membership in recurring series
CREATE TABLE IF NOT EXISTS recurring_tx (
    series_id TEXT NOT NULL,
    tx_id TEXT NOT NULL,
    PRIMARY KEY (series_id, tx_id),
    FOREIGN KEY (series_id) REFERENCES recurring_series(id),
    FOREIGN KEY (tx_id) REFERENCES transaction(id)
);

-- AI and Automation Tables

-- AI bulk processing jobs
CREATE TABLE IF NOT EXISTS ai_bulk_job (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,           -- categorize, enhance, dedupe
    total_transactions INTEGER NOT NULL,
    processed_transactions INTEGER DEFAULT 0,
    enhanced_transactions INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing', -- processing, completed, failed
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- AI workflow execution tracking
CREATE TABLE IF NOT EXISTS ai_workflow_run (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_transactions INTEGER DEFAULT 0,
    enhanced_transactions INTEGER DEFAULT 0,
    categorized_transactions INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    duplicates_merged INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    config_json TEXT,                 -- workflow configuration
    quality_report_json TEXT,         -- quality metrics
    errors_json TEXT                  -- error details
);

-- AI category mapping (external AI categories -> local categories)
CREATE TABLE IF NOT EXISTS ai_category_mapping (
    provider TEXT,                    -- openai, anthropic, local
    source_label TEXT NOT NULL,       -- AI provider's category
    category_id TEXT NOT NULL,        -- our local category
    PRIMARY KEY (provider, source_label),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- Audit and Logging

-- Complete audit trail for all changes
CREATE TABLE IF NOT EXISTS event_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,        -- transaction, category, rule, etc.
    entity_id TEXT NOT NULL,          -- ID of the affected entity
    action TEXT NOT NULL,             -- create, update, delete, classify
    payload_json TEXT,                -- change details as JSON
    ts TIMESTAMP NOT NULL,            -- timestamp of change
    actor TEXT                        -- user, system, rule_id, ai_provider
);

-- Example Category Data
INSERT OR IGNORE INTO category (id, name, parent_id) VALUES
('income', 'Income', NULL),
('salary', 'Salary', 'income'),
('freelance', 'Freelance', 'income'),
('investment', 'Investment Income', 'income'),

('expenses', 'Expenses', NULL),
('food', 'Food & Dining', 'expenses'),
('restaurants', 'Restaurants', 'food'),
('groceries', 'Groceries', 'food'),
('transportation', 'Transportation', 'expenses'),
('gas', 'Gas & Fuel', 'transportation'),
('public_transit', 'Public Transit', 'transportation'),
('utilities', 'Bills & Utilities', 'expenses'),
('internet', 'Internet', 'utilities'),
('phone', 'Phone', 'utilities'),
('electric', 'Electricity', 'utilities'),
('shopping', 'Shopping', 'expenses'),
('entertainment', 'Entertainment', 'expenses'),
('healthcare', 'Healthcare', 'expenses'),
('travel', 'Travel', 'expenses'),

('transfers', 'Transfers', NULL),
('internal', 'Internal Transfers', 'transfers'),
('external', 'External Transfers', 'transfers'),

('fees', 'Fees & Charges', NULL),
('bank_fees', 'Bank Fees', 'fees'),
('overdraft', 'Overdraft Fees', 'fees'),

('uncategorized', 'Uncategorized', NULL);

-- Example Institution Data
INSERT OR IGNORE INTO institution (id, name) VALUES
('boa', 'Bank of America'),
('chase', 'Chase Bank'),
('wells_fargo', 'Wells Fargo'),
('citi', 'Citibank'),
('capital_one', 'Capital One'),
('discover', 'Discover Bank'),
('amex', 'American Express'),
('local_credit_union', 'Local Credit Union');

-- Performance and Maintenance

-- Views for common queries
CREATE VIEW IF NOT EXISTS v_transaction_with_category AS
SELECT 
    t.*,
    c.name as category_name,
    c.parent_id as parent_category_id
FROM transaction t
LEFT JOIN transaction_category tc ON t.id = tc.tx_id
LEFT JOIN category c ON tc.category_id = c.id;

CREATE VIEW IF NOT EXISTS v_monthly_summary AS
SELECT 
    strftime('%Y-%m', posted_at) as month,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
    SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) as expenses,
    SUM(amount) as net_flow,
    COUNT(*) as transaction_count
FROM transaction
WHERE NOT EXISTS (
    SELECT 1 FROM match_transfer mt 
    WHERE (mt.left_tx_id = transaction.id OR mt.right_tx_id = transaction.id)
    AND mt.include_in_analytics = FALSE
)
GROUP BY strftime('%Y-%m', posted_at)
ORDER BY month;

-- Materialized aggregates for performance (recreate periodically)
CREATE TABLE IF NOT EXISTS agg_category_monthly AS
SELECT 
    strftime('%Y-%m', t.posted_at) as month,
    c.id as category_id,
    c.name as category_name,
    COUNT(*) as transaction_count,
    SUM(ABS(t.amount)) as total_amount,
    AVG(ABS(t.amount)) as avg_amount
FROM transaction t
JOIN transaction_category tc ON t.id = tc.tx_id
JOIN category c ON tc.category_id = c.id
WHERE t.amount < 0  -- expenses only
GROUP BY strftime('%Y-%m', t.posted_at), c.id, c.name;

-- Schema version tracking for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description) VALUES 
(1, 'Initial schema with core tables'),
(2, 'Added AI enhancement fields'),
(3, 'Added transfer detection and recurring analysis'),
(4, 'Added audit logging and performance views');

-- Comments explaining key design decisions:
--
-- 1. Fingerprinting: transactions.fingerprint ensures deduplication across re-imports
-- 2. Traceability: source_raw_id links back to original parsed data
-- 3. Flexibility: JSON fields for predicates/actions allow complex rules
-- 4. Performance: Indexes on account_id + posted_at for common queries
-- 5. AI Integration: Separate fields track AI processing without coupling
-- 6. Privacy: No PII in logs, sensitive data stays in main tables
-- 7. Audit: Complete change tracking for compliance and debugging
