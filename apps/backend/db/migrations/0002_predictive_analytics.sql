-- Phase 1: Predictive Analytics Schema
-- Add tables to support spending pattern analysis, forecasting, and smart insights

-- Spending patterns cache for performance
CREATE TABLE IF NOT EXISTS spending_patterns (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    category_id TEXT,
    category_name TEXT NOT NULL,
    month_year TEXT NOT NULL,
    amount_avg DOUBLE NOT NULL,
    amount_trend DOUBLE DEFAULT 0.0,
    frequency INTEGER DEFAULT 0,
    volatility DOUBLE DEFAULT 0.0,
    confidence_score DOUBLE DEFAULT 0.0,
    pattern_type TEXT DEFAULT 'regular', -- 'regular', 'seasonal', 'increasing', 'decreasing', 'sporadic'
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Seasonal patterns for better forecasting
CREATE TABLE IF NOT EXISTS seasonal_patterns (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL,
    category_name TEXT NOT NULL,
    month_number INTEGER NOT NULL, -- 1-12
    seasonal_multiplier DOUBLE NOT NULL DEFAULT 1.0,
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- Predictions cache with accuracy tracking
CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    prediction_type TEXT NOT NULL,  -- 'spending', 'income', 'balance', 'category'
    category_id TEXT,
    target_month TEXT NOT NULL, -- YYYY-MM format
    predicted_amount DOUBLE NOT NULL,
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    actual_amount DOUBLE,
    variance_pct DOUBLE,
    methodology TEXT, -- 'trend_analysis', 'seasonal_adjustment', 'ml_forecast'
    created_at TIMESTAMP DEFAULT now(),
    evaluated_at TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- Smart insights for user notifications
CREATE TABLE IF NOT EXISTS smart_insights (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    insight_type TEXT NOT NULL, -- 'spending_alert', 'budget_variance', 'unusual_transaction', 'goal_progress'
    priority INTEGER NOT NULL DEFAULT 5, -- 1-10, 10 being highest priority
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    amount DOUBLE,
    category_id TEXT,
    transaction_id TEXT,
    action_text TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    valid_until DATE,
    created_at TIMESTAMP DEFAULT now(),
    read_at TIMESTAMP,
    dismissed_at TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (category_id) REFERENCES category(id),
    FOREIGN KEY (transaction_id) REFERENCES transaction(id)
);

-- Financial goals tracking
CREATE TABLE IF NOT EXISTS financial_goals (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    goal_type TEXT NOT NULL, -- 'savings', 'spending_limit', 'debt_payoff', 'emergency_fund'
    category_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    target_amount DOUBLE NOT NULL,
    current_amount DOUBLE DEFAULT 0.0,
    target_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

-- Prediction accuracy tracking for model improvement
CREATE TABLE IF NOT EXISTS prediction_accuracy (
    id TEXT PRIMARY KEY,
    prediction_id TEXT NOT NULL,
    prediction_type TEXT NOT NULL,
    predicted_value DOUBLE NOT NULL,
    actual_value DOUBLE NOT NULL,
    accuracy_pct DOUBLE NOT NULL,
    absolute_error DOUBLE NOT NULL,
    evaluation_date DATE NOT NULL,
    methodology TEXT,
    created_at TIMESTAMP DEFAULT now(),
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_spending_patterns_account_month ON spending_patterns(account_id, month_year);
CREATE INDEX IF NOT EXISTS idx_spending_patterns_category ON spending_patterns(category_id);
CREATE INDEX IF NOT EXISTS idx_seasonal_patterns_category_month ON seasonal_patterns(category_id, month_number);
CREATE INDEX IF NOT EXISTS idx_predictions_account_type ON predictions(account_id, prediction_type);
CREATE INDEX IF NOT EXISTS idx_predictions_target_month ON predictions(target_month);
CREATE INDEX IF NOT EXISTS idx_smart_insights_account_priority ON smart_insights(account_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_smart_insights_unread ON smart_insights(account_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_financial_goals_account_active ON financial_goals(account_id, is_active);
CREATE INDEX IF NOT EXISTS idx_prediction_accuracy_type ON prediction_accuracy(prediction_type, evaluation_date);

-- Add AI analysis tracking columns to existing transaction table
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_predicted_category TEXT;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_prediction_confidence DOUBLE;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_anomaly_score DOUBLE;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_processed_at TIMESTAMP;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_provider TEXT;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_model TEXT;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_latency_ms INTEGER;

-- Add merchant insights
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_merchant_name TEXT;
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_category_suggestions TEXT; -- JSON array
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS ai_confidence_score DOUBLE;

-- Add transfer detection enhancement
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS is_transfer BOOLEAN DEFAULT FALSE;

-- Enhance recurring series with prediction capabilities
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS prediction_confidence DOUBLE DEFAULT 0.0;
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS next_predicted_amount DOUBLE;
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS last_date DATE;
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS next_date DATE;
ALTER TABLE recurring_series ADD COLUMN IF NOT EXISTS price_hike BOOLEAN DEFAULT FALSE;