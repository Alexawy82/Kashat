from __future__ import annotations

import duckdb  # type: ignore
from pathlib import Path
from typing import Optional
import threading
from .config import db_path


# Use a thread-local connection to avoid DuckDB "pending result" errors
_THREAD_LOCAL = threading.local()
# Guard to ensure schema/migrations run only once per process to avoid DuckDB
# write-write conflicts from concurrent connections.
_INIT_LOCK = threading.Lock()
_SCHEMA_APPLIED = False


SCHEMA_SQL = r"""
PRAGMA enable_object_cache;

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
    FOREIGN KEY (institution_id) REFERENCES institution(id)
);

CREATE TABLE IF NOT EXISTS import_run (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
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
    parsed_at TIMESTAMP NOT NULL,
    FOREIGN KEY (file_id) REFERENCES import_file(id)
);

CREATE TABLE IF NOT EXISTS transaction (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    posted_at DATE NOT NULL,
    amount DOUBLE NOT NULL,
    currency TEXT,
    description_norm TEXT NOT NULL,
    external_id TEXT,
    fingerprint TEXT NOT NULL,
    source_raw_id TEXT,
    is_business BOOLEAN NOT NULL DEFAULT FALSE,
    is_income BOOLEAN NOT NULL DEFAULT FALSE,
    is_adjustment BOOLEAN NOT NULL DEFAULT FALSE,
    zelle_direction TEXT,
    zelle_counterparty TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id)
);

CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transaction(account_id, posted_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tx_fingerprint ON transaction(fingerprint);

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
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS transaction_category (
    tx_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    applied_by TEXT,
    PRIMARY KEY (tx_id, category_id),
    FOREIGN KEY (tx_id) REFERENCES transaction(id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);

CREATE TABLE IF NOT EXISTS match_transfer (
    left_tx_id TEXT NOT NULL,
    right_tx_id TEXT NOT NULL,
    group_id TEXT,
    score DOUBLE,
    method TEXT,
    decided_at TIMESTAMP,
    PRIMARY KEY (left_tx_id, right_tx_id)
);

CREATE TABLE IF NOT EXISTS recurring_series (
    id TEXT PRIMARY KEY,
    name TEXT,
    cadence TEXT,
    anchor_day INTEGER,
    amount_mean DOUBLE,
    amount_sd DOUBLE,
    rule_ref TEXT
);

CREATE TABLE IF NOT EXISTS event_log (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT,
    ts TIMESTAMP NOT NULL,
    actor TEXT
);
"""


def _new_connection(dbfile: str) -> duckdb.DuckDBPyConnection:
    import time
    conn = duckdb.connect(dbfile)
    global _SCHEMA_APPLIED
    # Always ensure schema exists for the current database file.
    # In test environments the data dir may change between connections;
    # if a previous connection initialized a different DB file, tables
    # may be missing here even if _SCHEMA_APPLIED is True.
    needs_init = False
    if not _SCHEMA_APPLIED:
        needs_init = True
    else:
        # Best-effort check for a core table and initialize if missing
        try:
            conn.execute("SELECT 1 FROM account LIMIT 1")
        except Exception:
            needs_init = True

    if needs_init:
        with _INIT_LOCK:
            # Re-check inside lock to avoid races
            if (not _SCHEMA_APPLIED) or _table_missing(conn, "account"):
                # Apply schema with a single retry on DuckDB fatal invalidation to self-heal.
                for attempt in (1, 2):
                    try:
                        conn.execute(SCHEMA_SQL)
                        _upgrade_schema(conn)
                        _SCHEMA_APPLIED = True
                        break
                    except Exception as e:
                        msg = str(e)
                        # Retry once on invalidated database errors
                        if attempt == 1 and "invalidated" in msg.lower():
                            try:
                                conn.close()
                            except Exception:
                                pass
                            time.sleep(0.1)
                            conn = duckdb.connect(dbfile)
                            continue
                        raise
    return conn


def _table_missing(conn: duckdb.DuckDBPyConnection, name: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{name}' LIMIT 1")
        res = conn.fetchone()
        return not bool(res)
    except Exception:
        # Fallback: try selecting from the table; if it fails, it's missing
        try:
            conn.execute(f"SELECT 1 FROM {name} LIMIT 1")
            conn.fetchone()
            return False
        except Exception:
            return True


def connect(path: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    dbfile = str((path or db_path()))
    conn: Optional[duckdb.DuckDBPyConnection] = getattr(_THREAD_LOCAL, "conn", None)
    try:
        # duckdb connection has .close() but no explicit .closed flag; keep simple
        if conn is None:
            conn = _new_connection(dbfile)
            _THREAD_LOCAL.conn = conn
            return conn
        return conn
    except Exception:
        # On any issue, create a fresh connection
        conn = _new_connection(dbfile)
        _THREAD_LOCAL.conn = conn
        return conn


def get_conn() -> duckdb.DuckDBPyConnection:
    return connect()


def close() -> None:
    conn: Optional[duckdb.DuckDBPyConnection] = getattr(_THREAD_LOCAL, "conn", None)
    if conn is not None:
        conn.close()
        _THREAD_LOCAL.conn = None


def _upgrade_schema(conn: duckdb.DuckDBPyConnection) -> None:
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
    try:
        conn.execute("ALTER TABLE recurring_series ADD COLUMN status TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE recurring_series ADD COLUMN decided_at TIMESTAMP")
    except Exception:
        pass
    
    # Add AI-related columns to import_run table
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_enhanced_count INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_avg_quality_score FLOAT DEFAULT 0.0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_anomalies_detected INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_analysis_complete BOOLEAN DEFAULT FALSE")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_suggested_rules_count INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE import_run ADD COLUMN ai_workflow_id TEXT")
    except Exception:
        pass
    
    # Add AI bulk job tracking table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_bulk_job (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                total_transactions INTEGER NOT NULL,
                processed_transactions INTEGER DEFAULT 0,
                enhanced_transactions INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                created_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                error_message TEXT
            )
        """)
    except Exception:
        pass
    
    # Add AI workflow tracking table
    try:
        conn.execute("""
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
                config_json TEXT,
                quality_report_json TEXT,
                errors_json TEXT
            )
        """)
    except Exception:
        pass
    # Add transaction flags if missing
    for col in ("is_business BOOLEAN", "is_income BOOLEAN", "is_adjustment BOOLEAN"):
        try:
            conn.execute(f"ALTER TABLE transaction ADD COLUMN {col} DEFAULT FALSE")
        except Exception:
            pass
    for col in ("zelle_direction TEXT", "zelle_counterparty TEXT"):
        try:
            conn.execute(f"ALTER TABLE transaction ADD COLUMN {col}")
        except Exception:
            pass
    # Optional payee alias surfaced by rules/actions
    try:
        conn.execute("ALTER TABLE transaction ADD COLUMN payee_alias TEXT")
    except Exception:
        pass
    # Add group_id for transfers if missing
    try:
        conn.execute("ALTER TABLE match_transfer ADD COLUMN group_id TEXT")
    except Exception:
        pass
    # Include flag for analytics
    try:
        conn.execute("ALTER TABLE match_transfer ADD COLUMN include_in_analytics BOOLEAN DEFAULT FALSE")
    except Exception:
        pass
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
    for sql in (
        "ALTER TABLE recurring_series ADD COLUMN last_date DATE",
        "ALTER TABLE recurring_series ADD COLUMN next_date DATE",
        "ALTER TABLE recurring_series ADD COLUMN price_hike BOOLEAN",
    ):
        try:
            conn.execute(sql)
        except Exception:
            pass
    # Add AI-enhanced transaction fields
    for sql in (
        "ALTER TABLE transaction ADD COLUMN ai_merchant_name TEXT",
        "ALTER TABLE transaction ADD COLUMN ai_category_suggestions TEXT",
        "ALTER TABLE transaction ADD COLUMN ai_confidence_score FLOAT",
        "ALTER TABLE transaction ADD COLUMN ai_processed_at TIMESTAMP",
        "ALTER TABLE transaction ADD COLUMN ai_provider TEXT",
        "ALTER TABLE transaction ADD COLUMN ai_model TEXT",
        "ALTER TABLE transaction ADD COLUMN ai_latency_ms INTEGER",
    ):
        try:
            conn.execute(sql)
        except Exception:
            pass
    # AI category mapping table
    try:
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
    except Exception:
        pass
    # Migrate event_log column names if older schema exists
    try:
        conn.execute("ALTER TABLE event_log RENAME COLUMN at TO ts")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE event_log RENAME COLUMN by TO actor")
    except Exception:
        pass
    # Track ingestion linkage for safe deletions and analytics per run/file
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_ingest (
                tx_id TEXT PRIMARY KEY,
                run_id TEXT,
                file_id TEXT
            )
            """
        )
    except Exception:
        pass
