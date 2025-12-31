from __future__ import annotations

import sqlite3
import re
from pathlib import Path
from typing import Optional, Any, List, Tuple
import threading
import os
from datetime import datetime, timezone
from .config import db_path


def _sqlite_regexp(pattern: str, string: str) -> bool:
    """SQLite regexp function implementation using Python's re module.

    Note: This is called as REGEXP(pattern, string) - standard SQLite order.
    """
    if string is None:
        return False
    try:
        return bool(re.search(pattern, string, re.IGNORECASE))
    except Exception:
        return False


def _sqlite_regexp_matches(string: str, pattern: str) -> bool:
    """DuckDB-compatible regexp_matches(string, pattern) function.

    Note: DuckDB uses regexp_matches(string, pattern) - opposite order from SQLite.
    This wrapper swaps the arguments for compatibility.
    """
    if string is None or pattern is None:
        return False
    try:
        return bool(re.search(pattern, string, re.IGNORECASE))
    except Exception:
        return False


class SQLiteConnectionWrapper:
    """Wrapper to make SQLite connection work like DuckDB with .description on connection."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._last_cursor: Optional[sqlite3.Cursor] = None

    def execute(self, sql: str, params=None):
        """Execute SQL and store cursor for description access."""
        if params is None:
            self._last_cursor = self._conn.execute(sql)
        else:
            self._last_cursor = self._conn.execute(sql, params)
        return self._last_cursor

    def executemany(self, sql: str, params):
        """Execute SQL with multiple parameter sets."""
        self._last_cursor = self._conn.executemany(sql, params)
        return self._last_cursor

    def executescript(self, sql: str):
        """Execute multiple SQL statements."""
        return self._conn.executescript(sql)

    @property
    def description(self):
        """Return description from last cursor."""
        if self._last_cursor:
            return self._last_cursor.description
        return None

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def create_function(self, name, num_params, func):
        return self._conn.create_function(name, num_params, func)

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self._conn.row_factory = value


# Use a thread-local connection to avoid SQLite threading issues
_THREAD_LOCAL = threading.local()
# Guard to ensure schema/migrations run only once per process
_INIT_LOCK = threading.Lock()
_SCHEMA_APPLIED = False
_DBFILE_OVERRIDE: Optional[str] = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS institution (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    institution_id TEXT,
    name TEXT NOT NULL,
    type TEXT,
    last4 TEXT,
    currency TEXT,
    account_type TEXT DEFAULT 'checking',
    FOREIGN KEY (institution_id) REFERENCES institution(id)
);

CREATE TABLE IF NOT EXISTS import_run (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    source TEXT,
    user_note TEXT
);

CREATE TABLE IF NOT EXISTS import_file (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    path TEXT,
    hash TEXT,
    type TEXT,
    FOREIGN KEY (run_id) REFERENCES import_run(id)
);

CREATE TABLE IF NOT EXISTS raw_record (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    row_no INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    parsed_at TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES import_file(id)
);

CREATE TABLE IF NOT EXISTS [transaction] (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT,
    description_norm TEXT NOT NULL,
    external_id TEXT,
    fingerprint TEXT NOT NULL,
    source_raw_id TEXT,
    is_business INTEGER NOT NULL DEFAULT 0,
    is_income INTEGER NOT NULL DEFAULT 0,
    is_adjustment INTEGER NOT NULL DEFAULT 0,
    zelle_direction TEXT,
    zelle_counterparty TEXT,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by TEXT,
    FOREIGN KEY (account_id) REFERENCES account(id)
);

CREATE INDEX IF NOT EXISTS idx_tx_account_date ON [transaction](account_id, posted_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tx_fingerprint ON [transaction](fingerprint);

CREATE TABLE IF NOT EXISTS category (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT
);

CREATE TABLE IF NOT EXISTS rule (
    id TEXT PRIMARY KEY,
    priority INTEGER NOT NULL,
    predicate_json TEXT NOT NULL,
    action_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transaction_category (
    tx_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    applied_by TEXT,
    PRIMARY KEY (tx_id, category_id),
    FOREIGN KEY (tx_id) REFERENCES [transaction](id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

CREATE TABLE IF NOT EXISTS match_transfer (
    left_tx_id TEXT NOT NULL,
    right_tx_id TEXT NOT NULL,
    group_id TEXT,
    score REAL,
    method TEXT,
    decided_at TEXT,
    PRIMARY KEY (left_tx_id, right_tx_id)
);

CREATE TABLE IF NOT EXISTS recurring_series (
    id TEXT PRIMARY KEY,
    name TEXT,
    cadence TEXT,
    anchor_day INTEGER,
    amount_mean REAL,
    amount_sd REAL,
    rule_ref TEXT
);

CREATE TABLE IF NOT EXISTS event_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT,
    ts TEXT NOT NULL,
    actor TEXT
);

-- Budget System Tables
CREATE TABLE IF NOT EXISTS budget (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    period TEXT NOT NULL DEFAULT 'monthly',
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
    rollover INTEGER DEFAULT 0,
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

CREATE INDEX IF NOT EXISTS idx_budget_active ON budget(is_active);
CREATE INDEX IF NOT EXISTS idx_budget_category_budget ON budget_category(budget_id);
CREATE INDEX IF NOT EXISTS idx_budget_category_cat ON budget_category(category_id);

-- Net Worth Snapshot Table
CREATE TABLE IF NOT EXISTS networth_snapshot (
    id TEXT PRIMARY KEY,
    snapshot_date TEXT NOT NULL,
    total_assets REAL NOT NULL DEFAULT 0,
    total_liabilities REAL NOT NULL DEFAULT 0,
    net_worth REAL NOT NULL DEFAULT 0,
    breakdown_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_networth_date ON networth_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_tx_reviewed ON [transaction](reviewed_at);

-- ============================================================================
-- NET WORTH INTELLIGENCE TABLES
-- ============================================================================

-- Pending suggestions (before user confirms)
CREATE TABLE IF NOT EXISTS networth_suggestion (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    subtype TEXT,
    confidence REAL DEFAULT 0.5,
    source_recurring_id TEXT,
    source_data JSON,
    suggested_values JSON,
    status TEXT DEFAULT 'pending',
    snoozed_until TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    FOREIGN KEY (source_recurring_id) REFERENCES recurring_series(id)
);

-- Confirmed assets
CREATE TABLE IF NOT EXISTS asset (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    subtype TEXT,
    name TEXT NOT NULL,
    current_value REAL,
    purchase_price REAL,
    purchase_date TEXT,
    details JSON,
    linked_recurring_id TEXT,
    linked_liability_id TEXT,
    suggestion_id TEXT,
    enrichment_source TEXT,
    enrichment_data JSON,
    last_enriched_at TEXT,
    auto_refresh INTEGER DEFAULT 1,
    milestones_json JSON,
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (linked_recurring_id) REFERENCES recurring_series(id)
);

-- Confirmed liabilities
CREATE TABLE IF NOT EXISTS liability (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    lender TEXT,
    original_amount REAL,
    current_balance REAL,
    interest_rate REAL,
    monthly_payment REAL,
    term_months INTEGER,
    start_date TEXT,
    expected_payoff_date TEXT,
    linked_recurring_id TEXT,
    linked_asset_id TEXT,
    suggestion_id TEXT,
    auto_calculate_balance INTEGER DEFAULT 1,
    milestones_json JSON,
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (linked_recurring_id) REFERENCES recurring_series(id),
    FOREIGN KEY (linked_asset_id) REFERENCES asset(id)
);

-- Track payments against liabilities
CREATE TABLE IF NOT EXISTS liability_payment (
    id TEXT PRIMARY KEY,
    liability_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL,
    principal_portion REAL,
    interest_portion REAL,
    balance_after REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (liability_id) REFERENCES liability(id),
    FOREIGN KEY (transaction_id) REFERENCES [transaction](id),
    UNIQUE(liability_id, transaction_id)
);

-- Enrichment cache
CREATE TABLE IF NOT EXISTS enrichment_cache (
    id TEXT PRIMARY KEY,
    cache_key TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    data JSON NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Net worth settings
CREATE TABLE IF NOT EXISTS networth_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    property_refresh_days INTEGER DEFAULT 30,
    vehicle_refresh_days INTEGER DEFAULT 7,
    metal_refresh_hours INTEGER DEFAULT 1,
    stock_refresh_minutes INTEGER DEFAULT 15,
    notify_milestones INTEGER DEFAULT 1,
    notify_appreciation INTEGER DEFAULT 1,
    notify_suggestions INTEGER DEFAULT 1,
    milestone_thresholds JSON DEFAULT '[10, 20, 25, 50, 75, 100]',
    show_suggestions_on_dashboard INTEGER DEFAULT 1,
    default_property_source TEXT DEFAULT 'manual',
    default_vehicle_source TEXT DEFAULT 'manual',
    achieved_milestones JSON DEFAULT '[]',
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Net Worth Intelligence Indexes
CREATE INDEX IF NOT EXISTS idx_asset_type ON asset(type);
CREATE INDEX IF NOT EXISTS idx_asset_linked_recurring ON asset(linked_recurring_id);
CREATE INDEX IF NOT EXISTS idx_liability_type ON liability(type);
CREATE INDEX IF NOT EXISTS idx_liability_linked_recurring ON liability(linked_recurring_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_status ON networth_suggestion(status);
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_key ON enrichment_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_liability_payment_liability ON liability_payment(liability_id);

-- ============================================================================
-- BUDGET INTELLIGENCE TABLES
-- ============================================================================

-- Income sources detected from transactions
CREATE TABLE IF NOT EXISTS income_source (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'salary', 'side_income', 'investment', 'transfer', 'refund', 'other'

    -- Detection data
    avg_amount REAL,
    frequency TEXT,  -- 'weekly', 'biweekly', 'monthly', 'irregular'
    confidence REAL DEFAULT 0.5,

    -- Pattern matching
    pattern_description TEXT,
    last_detected_at TEXT,
    occurrence_count INTEGER DEFAULT 0,

    -- User overrides
    user_confirmed BOOLEAN DEFAULT FALSE,
    user_amount_override REAL,
    user_name_override TEXT,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Budget suggestions (AI-generated, pending user review)
CREATE TABLE IF NOT EXISTS budget_suggestion (
    id TEXT PRIMARY KEY,

    -- Suggestion type
    type TEXT NOT NULL,  -- 'full_budget', 'category_limit', 'adjustment', 'seasonal'

    -- For category-level suggestions
    category_id TEXT,
    category_name TEXT,

    -- Suggested values
    suggested_limit REAL,
    current_avg_spending REAL,
    spending_trend TEXT,  -- 'increasing', 'decreasing', 'stable', 'volatile'
    trend_percentage REAL,

    -- Reasoning
    reason TEXT,
    confidence REAL DEFAULT 0.5,

    -- Context
    based_on_months INTEGER,
    seasonality_factor REAL,

    -- Status
    status TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'dismissed', 'snoozed'
    snoozed_until TEXT,

    -- If accepted, link to budget
    applied_to_budget_id TEXT,

    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,

    FOREIGN KEY (category_id) REFERENCES category(id),
    FOREIGN KEY (applied_to_budget_id) REFERENCES budget(id)
);

-- Link recurring series to budget categories
CREATE TABLE IF NOT EXISTS budget_recurring_link (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    budget_category_id TEXT NOT NULL,
    recurring_series_id TEXT NOT NULL,

    -- Tracking
    is_committed BOOLEAN DEFAULT TRUE,

    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (budget_id) REFERENCES budget(id) ON DELETE CASCADE,
    FOREIGN KEY (budget_category_id) REFERENCES budget_category(id) ON DELETE CASCADE,
    FOREIGN KEY (recurring_series_id) REFERENCES recurring_series(id)
);

-- Budget pace snapshots (for tracking overspending trajectory)
CREATE TABLE IF NOT EXISTS budget_pace_snapshot (
    id TEXT PRIMARY KEY,
    budget_id TEXT NOT NULL,
    budget_category_id TEXT,  -- NULL for overall budget

    snapshot_date TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,

    -- Current state
    days_elapsed INTEGER,
    days_remaining INTEGER,
    amount_spent REAL,
    amount_limit REAL,

    -- Projections
    daily_rate REAL,
    projected_total REAL,
    projected_over_under REAL,  -- Positive = over, negative = under
    exceed_date TEXT,  -- NULL if won't exceed

    -- Status
    status TEXT,  -- 'on_track', 'at_risk', 'will_exceed', 'exceeded'

    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (budget_id) REFERENCES budget(id) ON DELETE CASCADE,
    FOREIGN KEY (budget_category_id) REFERENCES budget_category(id) ON DELETE CASCADE
);

-- Budget settings
CREATE TABLE IF NOT EXISTS budget_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',

    -- Income settings
    include_irregular_income BOOLEAN DEFAULT FALSE,
    income_buffer_percent REAL DEFAULT 0.0,

    -- Budget defaults
    default_period TEXT DEFAULT 'monthly',
    auto_rollover BOOLEAN DEFAULT FALSE,

    -- Alert settings
    pace_warning_threshold REAL DEFAULT 0.8,
    alert_days_before_exceed INTEGER DEFAULT 5,

    -- Suggestion settings
    suggest_from_spending BOOLEAN DEFAULT TRUE,
    seasonal_adjustments BOOLEAN DEFAULT TRUE,
    savings_goal_percent REAL DEFAULT 0.20,

    -- Display preferences
    show_committed_separate BOOLEAN DEFAULT TRUE,
    show_pace_tracking BOOLEAN DEFAULT TRUE,

    updated_at TEXT DEFAULT (datetime('now'))
);

-- Budget Intelligence Indexes
CREATE INDEX IF NOT EXISTS idx_income_source_type ON income_source(type);
CREATE INDEX IF NOT EXISTS idx_income_source_active ON income_source(is_active);
CREATE INDEX IF NOT EXISTS idx_budget_suggestion_status ON budget_suggestion(status);
CREATE INDEX IF NOT EXISTS idx_budget_suggestion_category ON budget_suggestion(category_id);
CREATE INDEX IF NOT EXISTS idx_budget_recurring_link_budget ON budget_recurring_link(budget_id);
CREATE INDEX IF NOT EXISTS idx_budget_pace_snapshot_budget ON budget_pace_snapshot(budget_id);
CREATE INDEX IF NOT EXISTS idx_budget_pace_snapshot_date ON budget_pace_snapshot(snapshot_date);
"""


def _now_iso() -> str:
    """Return current UTC time as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def _new_connection(dbfile: str) -> sqlite3.Connection:
    """Create a new SQLite connection with proper settings."""
    # Use isolation_level=None for autocommit mode (matches DuckDB behavior)
    conn = sqlite3.connect(dbfile, check_same_thread=False, isolation_level=None)
    # Register custom functions
    conn.create_function("regexp", 2, _sqlite_regexp)
    conn.create_function("regexp_matches", 2, _sqlite_regexp_matches)  # DuckDB compatibility alias
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    # Use WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode = WAL")
    # Set busy timeout to 30 seconds
    conn.execute("PRAGMA busy_timeout = 30000")
    # Return rows as sqlite3.Row for dict-like access
    conn.row_factory = sqlite3.Row

    global _SCHEMA_APPLIED
    needs_init = False
    if not _SCHEMA_APPLIED:
        needs_init = True
    else:
        # Best-effort check for a core table
        try:
            conn.execute("SELECT 1 FROM account LIMIT 1")
        except Exception:
            needs_init = True

    if needs_init:
        with _INIT_LOCK:
            if (not _SCHEMA_APPLIED) or _table_missing(conn, "account"):
                try:
                    # Execute schema statements one by one (SQLite doesn't support multiple statements with executescript in same manner)
                    conn.executescript(SCHEMA_SQL)
                    _upgrade_schema(conn)
                    _ensure_schema_version_table(conn)
                    _run_migrations(conn)
                    conn.commit()
                    _SCHEMA_APPLIED = True
                except Exception as e:
                    conn.rollback()
                    raise

    # Track the dbfile bound to this thread-local connection
    try:
        _THREAD_LOCAL.dbfile = dbfile
    except Exception:
        pass
    return conn


def _table_missing(conn: sqlite3.Connection, name: str) -> bool:
    """Check if a table is missing from the database."""
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [name]
        )
        res = cursor.fetchone()
        return not bool(res)
    except Exception:
        return True


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except Exception:
        return False


def connect(path: Optional[Path] = None) -> SQLiteConnectionWrapper:
    """Get or create a thread-local SQLite connection."""
    # SQLite uses .sqlite extension
    base = str((path or db_path()))
    # Convert .duckdb extension to .sqlite if present
    if base.endswith('.duckdb'):
        base = base[:-7] + '.sqlite'
    dbfile = _DBFILE_OVERRIDE or base

    wrapper: Optional[SQLiteConnectionWrapper] = getattr(_THREAD_LOCAL, "conn", None)
    bound: Optional[str] = getattr(_THREAD_LOCAL, "dbfile", None)
    try:
        # Rebind connection if target dbfile changed
        if (wrapper is None) or (bound and bound != dbfile):
            if wrapper is not None:
                try:
                    wrapper.close()
                except Exception:
                    pass
            raw_conn = _new_connection(dbfile)
            wrapper = SQLiteConnectionWrapper(raw_conn)
            _THREAD_LOCAL.conn = wrapper
            return wrapper
        return wrapper
    except Exception:
        raw_conn = _new_connection(dbfile)
        wrapper = SQLiteConnectionWrapper(raw_conn)
        _THREAD_LOCAL.conn = wrapper
        return wrapper


def get_conn() -> SQLiteConnectionWrapper:
    """Alias for connect()."""
    return connect()


def close() -> None:
    """Close the thread-local connection if open."""
    conn: Optional[sqlite3.Connection] = getattr(_THREAD_LOCAL, "conn", None)
    if conn is not None:
        conn.close()
    _THREAD_LOCAL.conn = None


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, coltype: str, default: Optional[str] = None) -> None:
    """Add a column to a table if it doesn't exist."""
    if not _column_exists(conn, table, column):
        default_clause = f" DEFAULT {default}" if default is not None else ""
        try:
            # Use bracket notation for reserved keyword tables like 'transaction'
            conn.execute(f"ALTER TABLE [{table}] ADD COLUMN {column} {coltype}{default_clause}")
        except Exception:
            pass


def _upgrade_schema(conn: sqlite3.Connection) -> None:
    """Best-effort schema upgrades that are safe to run multiple times."""
    # Add recurring membership table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS recurring_tx (
            series_id TEXT NOT NULL,
            tx_id TEXT NOT NULL,
            PRIMARY KEY (series_id, tx_id)
        )
        """
    )

    # Add status/decided_at to recurring_series if missing
    _add_column_if_missing(conn, "recurring_series", "status", "TEXT")
    _add_column_if_missing(conn, "recurring_series", "decided_at", "TEXT")

    # Add AI-related columns to import_run table
    _add_column_if_missing(conn, "import_run", "ai_enhanced_count", "INTEGER", "0")
    _add_column_if_missing(conn, "import_run", "ai_avg_quality_score", "REAL", "0.0")
    _add_column_if_missing(conn, "import_run", "ai_anomalies_detected", "INTEGER", "0")
    _add_column_if_missing(conn, "import_run", "ai_analysis_complete", "INTEGER", "0")
    _add_column_if_missing(conn, "import_run", "ai_suggested_rules_count", "INTEGER", "0")
    _add_column_if_missing(conn, "import_run", "ai_workflow_id", "TEXT")

    # Add AI bulk job tracking table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_bulk_job (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            total_transactions INTEGER NOT NULL,
            processed_transactions INTEGER DEFAULT 0,
            enhanced_transactions INTEGER DEFAULT 0,
            status TEXT DEFAULT 'processing',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT
        )
    """)

    # Helpful indexes for import analytics
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transaction_ingest_run ON transaction_ingest(run_id)")
    except Exception:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transaction_ingest_file ON transaction_ingest(file_id)")
    except Exception:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_import_file_run ON import_file(run_id)")
    except Exception:
        pass

    # Add AI workflow tracking table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_workflow_run (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_transactions INTEGER DEFAULT 0,
            enhanced_transactions INTEGER DEFAULT 0,
            categorized_transactions INTEGER DEFAULT 0,
            duplicates_found INTEGER DEFAULT 0,
            duplicates_merged INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            config_json TEXT,
            quality_report_json TEXT,
            errors_json TEXT
        )
    """)

    # Add transaction flags if missing
    for col, default in [("is_business", "0"), ("is_income", "0"), ("is_adjustment", "0")]:
        _add_column_if_missing(conn, "transaction", col, "INTEGER", default)

    for col in ["zelle_direction", "zelle_counterparty", "p2p_provider", "p2p_direction", "p2p_counterparty", "payee_alias"]:
        _add_column_if_missing(conn, "transaction", col, "TEXT")

    # Add group_id and include_in_analytics for transfers if missing
    _add_column_if_missing(conn, "match_transfer", "group_id", "TEXT")
    _add_column_if_missing(conn, "match_transfer", "include_in_analytics", "INTEGER", "0")

    # Simple tag table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transaction_tag (
            tx_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (tx_id, tag)
        )
        """
    )

    # Extend recurring_series with new fields
    recurring_cols = [
        ("first_date", "TEXT"),  # First transaction date in the series
        ("last_date", "TEXT"),
        ("next_date", "TEXT"),
        ("occurrences", "INTEGER"),  # Number of transactions in the series
        ("price_hike", "INTEGER"),
        ("recurring_type", "TEXT"),
        ("sub_category", "TEXT"),
        ("is_essential", "INTEGER", "0"),
        ("annual_cost", "REAL"),
        ("predicted_end_date", "TEXT"),
        ("lender_name", "TEXT"),
        ("estimated_remaining", "INTEGER"),
        ("display_name", "TEXT"),
        ("series_key", "TEXT"),
        ("account_id", "TEXT"),  # Link to account for calendar
        ("llm_confidence", "REAL"),
        ("llm_provider", "TEXT"),
        ("llm_classified_at", "TEXT"),
        ("prediction_confidence", "REAL"),
        ("next_predicted_amount", "REAL"),
        ("series_type", "TEXT"),  # "standard" or "p2p_recurring" - distinguishes P2P-originated recurring
        ("p2p_counterparty_id", "TEXT"),  # Link to counterparty table for P2P recurring
        ("p2p_service", "TEXT"),  # venmo, zelle, cashapp, paypal, etc. for P2P recurring
        ("linked_asset_id", "TEXT"),  # Link to asset table for mortgages/loans
        ("linked_liability_id", "TEXT"),  # Link to liability table for mortgages/loans
    ]
    for item in recurring_cols:
        col, coltype = item[0], item[1]
        default = item[2] if len(item) > 2 else None
        _add_column_if_missing(conn, "recurring_series", col, coltype, default)

    # Add recurring_series indexes
    for idx_sql in (
        "CREATE INDEX IF NOT EXISTS idx_recurring_series_key ON recurring_series(series_key)",
        "CREATE INDEX IF NOT EXISTS idx_recurring_status ON recurring_series(status)",
        "CREATE INDEX IF NOT EXISTS idx_recurring_type ON recurring_series(recurring_type)",
        "CREATE INDEX IF NOT EXISTS idx_recurring_next_date ON recurring_series(next_date)",
    ):
        try:
            conn.execute(idx_sql)
        except Exception:
            pass

    # Add AI-enhanced transaction fields
    ai_tx_cols = [
        ("ai_merchant_name", "TEXT"),
        ("ai_category_suggestions", "TEXT"),
        ("ai_confidence_score", "REAL"),
        ("ai_processed_at", "TEXT"),
        ("ai_provider", "TEXT"),
        ("ai_model", "TEXT"),
        ("ai_latency_ms", "INTEGER"),
    ]
    for col, coltype in ai_tx_cols:
        _add_column_if_missing(conn, "transaction", col, coltype)

    # AI category mapping table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_category_mapping (
            provider TEXT,
            source_label TEXT NOT NULL,
            category_id TEXT NOT NULL,
            PRIMARY KEY (provider, source_label)
        )
        """
    )

    # AI suggestion opt-out table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_suggestion_opt_out (
            merchant TEXT NOT NULL,
            category_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (merchant, category_name)
        )
        """
    )

    # Workflow persistence table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_state (
            id TEXT PRIMARY KEY,
            type TEXT,
            status TEXT,
            state_json TEXT NOT NULL,
            created_ts TEXT NOT NULL,
            updated_ts TEXT NOT NULL
        )
        """
    )

    # Track ingestion linkage
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transaction_ingest (
            tx_id TEXT PRIMARY KEY,
            run_id TEXT,
            file_id TEXT
        )
        """
    )

    # Merchant memory system
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merchant_category_mapping (
            id TEXT PRIMARY KEY,
            merchant_name TEXT NOT NULL,
            merchant_pattern TEXT NOT NULL,
            category_id TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            confidence_i INTEGER,
            usage_count INTEGER DEFAULT 1,
            last_used TEXT,
            created_at TEXT,
            UNIQUE(merchant_pattern, category_id)
        )
        """
    )

    # Add normalized_name to category if missing
    _add_column_if_missing(conn, "category", "normalized_name", "TEXT")

    # Backfill normalized names
    try:
        conn.execute("UPDATE category SET normalized_name = lower(trim(name)) WHERE normalized_name IS NULL OR normalized_name = ''")
    except Exception:
        pass

    # Merchant Intelligence Cache
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merchant_intelligence_cache (
            id TEXT PRIMARY KEY,
            raw_description TEXT NOT NULL,
            description_hash TEXT NOT NULL,
            clean_merchant_name TEXT,
            recurring_type TEXT,
            sub_category TEXT,
            is_essential INTEGER,
            confidence REAL DEFAULT 0.0,
            provider TEXT,
            model TEXT,
            latency_ms INTEGER,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            hit_count INTEGER DEFAULT 0,
            last_hit_at TEXT,
            UNIQUE(description_hash)
        )
        """
    )

    # Index for fast lookups by description hash
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mic_hash ON merchant_intelligence_cache(description_hash)")
    except Exception:
        pass

    # P2P Transaction tracking table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS p2p_transaction (
            id TEXT PRIMARY KEY,
            tx_id TEXT NOT NULL,
            service TEXT NOT NULL,
            counterparty_raw TEXT,
            counterparty_normalized TEXT,
            direction TEXT,
            confidence REAL DEFAULT 1.0,
            detection_method TEXT,
            ai_analyzed_at TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (tx_id) REFERENCES [transaction](id)
        )
        """
    )
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_p2p_tx ON p2p_transaction(tx_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_p2p_counterparty ON p2p_transaction(counterparty_normalized)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_p2p_service ON p2p_transaction(service)")
    except Exception:
        pass

    # P2P transaction enrichment columns
    _add_column_if_missing(conn, "p2p_transaction", "transaction_type", "TEXT")  # p2p_transfer, subscription, purchase
    _add_column_if_missing(conn, "p2p_transaction", "counterparty_type", "TEXT")  # person, business, unknown
    _add_column_if_missing(conn, "p2p_transaction", "merchant_category", "TEXT")  # entertainment, utilities, etc.
    _add_column_if_missing(conn, "p2p_transaction", "ai_enriched_at", "TEXT")
    _add_column_if_missing(conn, "p2p_transaction", "ai_confidence", "REAL")
    _add_column_if_missing(conn, "p2p_transaction", "is_recurring", "INTEGER", "0")
    _add_column_if_missing(conn, "p2p_transaction", "recurring_series_id", "TEXT")  # Link to recurring_series if applicable

    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_p2p_type ON p2p_transaction(transaction_type)")
    except Exception:
        pass

    # Counterparty tracking table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS counterparty (
            id TEXT PRIMARY KEY,
            name_normalized TEXT NOT NULL UNIQUE,
            aliases TEXT,
            total_sent REAL DEFAULT 0,
            total_received REAL DEFAULT 0,
            transaction_count INTEGER DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT,
            is_recurring INTEGER DEFAULT 0,
            notes TEXT
        )
        """
    )
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_counterparty_name ON counterparty(name_normalized)")
    except Exception:
        pass

    # Counterparty enrichment columns
    _add_column_if_missing(conn, "counterparty", "counterparty_type", "TEXT")  # person, business, unknown
    _add_column_if_missing(conn, "counterparty", "category", "TEXT")  # merchant category if business

    # Ensure uniqueness on category normalized_name
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_category_normalized ON category(normalized_name)")
    except Exception:
        pass

    # Initialize default networth settings
    try:
        conn.execute("INSERT OR IGNORE INTO networth_settings (id) VALUES ('default')")
    except Exception:
        pass

    # =========================================================================
    # BUDGET INTELLIGENCE UPGRADES
    # =========================================================================

    # Add columns to existing budget table
    budget_cols = [
        ("income_target", "REAL"),
        ("savings_target", "REAL"),
        ("auto_suggested", "BOOLEAN", "FALSE"),
        ("last_pace_check", "TEXT"),
    ]
    for item in budget_cols:
        col, coltype = item[0], item[1]
        default = item[2] if len(item) > 2 else None
        _add_column_if_missing(conn, "budget", col, coltype, default)

    # Add columns to existing budget_category table
    budget_category_cols = [
        ("is_committed", "BOOLEAN", "FALSE"),
        ("source", "TEXT", "'manual'"),  # 'manual', 'suggested', 'recurring'
        ("trend", "TEXT"),  # 'increasing', 'decreasing', 'stable'
        ("avg_actual", "REAL"),  # Actual avg spending
        ("linked_recurring_id", "TEXT"),
    ]
    for item in budget_category_cols:
        col, coltype = item[0], item[1]
        default = item[2] if len(item) > 2 else None
        _add_column_if_missing(conn, "budget_category", col, coltype, default)

    # Initialize default budget settings
    try:
        conn.execute("INSERT OR IGNORE INTO budget_settings (id) VALUES ('default')")
    except Exception:
        pass

    conn.commit()


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    """Ensure the schema_version table exists and has a baseline entry."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    cursor = conn.execute("SELECT COUNT(1) FROM schema_version")
    row = cursor.fetchone()
    if not row or (row[0] == 0):
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            [1, _now_iso()]
        )
    conn.commit()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run pending SQL migrations from apps/backend/db/migrations (numeric order)."""
    try:
        # Compute repo root
        p = Path(__file__).resolve()
        repo_root = p.parents[4] if len(p.parents) >= 5 else p.parents[-1]
        mig_dir = repo_root / "apps" / "backend" / "db" / "migrations"
        if not mig_dir.exists():
            alt_root = p.parents[3] if len(p.parents) >= 4 else repo_root
            alt = alt_root / "apps" / "backend" / "db" / "migrations"
            if alt.exists():
                mig_dir = alt
        mig_dir.mkdir(parents=True, exist_ok=True)

        # Current version
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        v = row[0] if row and row[0] else 1

        files = sorted([p for p in mig_dir.glob("*.sql") if p.name[:4].isdigit()])
        for f in files:
            try:
                ver = int(f.name.split("_", 1)[0])
            except Exception:
                continue
            if ver <= v:
                continue
            sql = f.read_text()
            if not sql.strip():
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    [ver, _now_iso()]
                )
                v = ver
                continue
            # Run migration
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    [ver, _now_iso()]
                )
                conn.commit()
                v = ver
            except Exception:
                conn.rollback()
                raise
    except Exception:
        # migrations are best-effort
        pass
