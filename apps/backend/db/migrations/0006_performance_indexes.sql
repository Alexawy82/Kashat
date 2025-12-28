-- Performance indexes for common query patterns
-- Migration 0006: Performance Indexes

-- Transaction table indexes
CREATE INDEX IF NOT EXISTS idx_tx_ai_processed ON [transaction](ai_processed_at);
CREATE INDEX IF NOT EXISTS idx_tx_is_business ON [transaction](is_business);
CREATE INDEX IF NOT EXISTS idx_tx_is_income ON [transaction](is_income);
CREATE INDEX IF NOT EXISTS idx_tx_posted_month ON [transaction](substr(posted_at, 1, 7));
CREATE INDEX IF NOT EXISTS idx_tx_account_posted ON [transaction](account_id, posted_at);
CREATE INDEX IF NOT EXISTS idx_tx_category_posted ON [transaction](category_id, posted_at);

-- Transaction category mapping indexes
CREATE INDEX IF NOT EXISTS idx_txcat_category ON transaction_category(category_id);
CREATE INDEX IF NOT EXISTS idx_txcat_tx ON transaction_category(tx_id);

-- Merchant category mapping indexes
CREATE INDEX IF NOT EXISTS idx_mcm_merchant ON merchant_category_mapping(merchant_name);
CREATE INDEX IF NOT EXISTS idx_mcm_normalized ON merchant_category_mapping(normalized_pattern);
CREATE INDEX IF NOT EXISTS idx_mcm_category ON merchant_category_mapping(category_id);

-- Recurring series indexes
CREATE INDEX IF NOT EXISTS idx_recurring_next ON recurring_series(next_date);
CREATE INDEX IF NOT EXISTS idx_recurring_status ON recurring_series(status);
CREATE INDEX IF NOT EXISTS idx_recurring_type ON recurring_series(recurring_type);

-- Import run indexes
CREATE INDEX IF NOT EXISTS idx_import_run_date ON import_run(started_at);
CREATE INDEX IF NOT EXISTS idx_import_run_status ON import_run(status);

-- Import file indexes
CREATE INDEX IF NOT EXISTS idx_import_file_run ON import_file(run_id);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- Category indexes
CREATE INDEX IF NOT EXISTS idx_category_parent ON category(parent_id);
