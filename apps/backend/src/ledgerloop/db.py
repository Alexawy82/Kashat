from __future__ import annotations

import duckdb  # type: ignore
from pathlib import Path
from typing import Optional
import threading
import os
from .config import db_path


# Use a thread-local connection to avoid DuckDB "pending result" errors
_THREAD_LOCAL = threading.local()
# Guard to ensure schema/migrations run only once per process to avoid DuckDB
# write-write conflicts from concurrent connections.
_INIT_LOCK = threading.Lock()
_SCHEMA_APPLIED = False
_DBFILE_OVERRIDE: Optional[str] = None


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
    # Optional: cap DuckDB threads via env or settings
    try:
        import os as _os
        threads_env = _os.getenv("LEDGERLOOP_DUCKDB_THREADS")
        threads = int(threads_env) if threads_env else 0
        if threads <= 0:
            try:
                from .settings import load_settings as _load_settings
                threads = int(_load_settings().get("duckdb_threads", 0) or 0)
            except Exception:
                threads = 0
        if threads and threads > 0:
            conn.execute(f"PRAGMA threads={threads}")
    except Exception:
        pass
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
                        _ensure_schema_version_table(conn)
                        _run_migrations(conn)
                        _SCHEMA_APPLIED = True
                        break
                    except Exception as e:
                        msg = str(e).lower()
                        # Retry once on invalidated database or permission errors
                        recoverable = "invalidated" in msg or "permission denied" in msg or "read-only" in msg
                        if attempt == 1 and recoverable:
                            try:
                                conn.close()
                            except Exception:
                                pass
                            time.sleep(0.1)
                            conn = duckdb.connect(dbfile)
                            continue
                        # Robust fallback: pivot to a fresh DB file for this process
                        # if errors keep happening. Controlled by env (default: true).
                        allow_fallback = (os.getenv("LEDGERLOOP_DB_FALLBACK_ON_INVALIDATION", "true").lower() == "true")
                        if allow_fallback and (attempt == 2) and recoverable:
                            try:
                                from .config import tmp_dir  # late import
                                fb_dir = tmp_dir()
                                fb_path = fb_dir / f"ledgerloop-fallback-{int(time.time()*1000)}.duckdb"
                                fb_conn = duckdb.connect(str(fb_path))
                                fb_conn.execute(SCHEMA_SQL)
                                _upgrade_schema(fb_conn)
                                _ensure_schema_version_table(fb_conn)
                                _run_migrations(fb_conn)
                                # Switch global override so future connections use fallback file
                                global _DBFILE_OVERRIDE
                                _DBFILE_OVERRIDE = str(fb_path)
                                conn = fb_conn
                                _SCHEMA_APPLIED = True
                                print(f"[ledgerloop.db] Pivoted to fallback DB: {fb_path}")
                                break
                            except Exception:
                                pass
                        raise
    # Track the dbfile bound to this thread-local connection
    try:
        _THREAD_LOCAL.dbfile = dbfile
    except Exception:
        pass
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
    basefile = str((path or db_path()))
    dbfile = _DBFILE_OVERRIDE or basefile
    conn: Optional[duckdb.DuckDBPyConnection] = getattr(_THREAD_LOCAL, "conn", None)
    bound: Optional[str] = getattr(_THREAD_LOCAL, "dbfile", None)
    try:
        # duckdb connection has .close() but no explicit .closed flag; keep simple
        # Rebind connection if target dbfile changed (e.g., tests override LEDGERLOOP_DATA_DIR)
        if (conn is None) or (bound and bound != dbfile):
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
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
    # P2P provider parsing (Venmo/Cash App/Western Union, etc.)
    for col in ("p2p_provider TEXT", "p2p_direction TEXT", "p2p_counterparty TEXT"):
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
        # Phase 1: Enhanced detection fields
        "ALTER TABLE recurring_series ADD COLUMN recurring_type TEXT",  # subscription, bill, loan, credit_card
        "ALTER TABLE recurring_series ADD COLUMN sub_category TEXT",    # streaming, utility_electric, auto_loan, etc.
        "ALTER TABLE recurring_series ADD COLUMN is_essential BOOLEAN DEFAULT FALSE",
        "ALTER TABLE recurring_series ADD COLUMN annual_cost DOUBLE",
        "ALTER TABLE recurring_series ADD COLUMN predicted_end_date DATE",  # For loans
        "ALTER TABLE recurring_series ADD COLUMN lender_name TEXT",  # Clean lender name for loans
        "ALTER TABLE recurring_series ADD COLUMN estimated_remaining INTEGER",  # Remaining payments for loans
        # Display and dedup fields (consolidated from recurring.py)
        "ALTER TABLE recurring_series ADD COLUMN display_name TEXT",
        "ALTER TABLE recurring_series ADD COLUMN series_key TEXT",
    ):
        try:
            conn.execute(sql)
        except Exception:
            pass
    # Add recurring_series indexes for faster lookups
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
    # Ensure merchant_category_mapping.confidence uses DOUBLE (64-bit) for Python float equality behavior
    try:
        conn.execute("ALTER TABLE merchant_category_mapping ALTER COLUMN confidence TYPE DOUBLE")
    except Exception:
        pass
    # Migrate event_log column names if older schema exists
    try:
        conn.execute("ALTER TABLE event_log RENAME COLUMN at TO ts")
    except Exception:
        pass
    # AI suggestion opt-out table
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_suggestion_opt_out (
                merchant TEXT NOT NULL,
                category_name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                PRIMARY KEY (merchant, category_name)
            )
            """
        )
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE event_log RENAME COLUMN by TO actor")
    except Exception:
        pass
    # Workflow persistence table
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_state (
                id TEXT PRIMARY KEY,
                type TEXT,
                status TEXT,
                state_json TEXT NOT NULL,
                created_ts TIMESTAMP NOT NULL,
                updated_ts TIMESTAMP NOT NULL
            )
            """
        )
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
    
    # Merchant memory system for learning categorizations
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS merchant_category_mapping (
                id TEXT PRIMARY KEY,
                merchant_name TEXT NOT NULL,
                merchant_pattern TEXT NOT NULL,
                category_id TEXT NOT NULL,
                confidence FLOAT DEFAULT 1.0,
                confidence_i INTEGER,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                created_at TIMESTAMP,
                UNIQUE(merchant_pattern, category_id)
            )
            """
        )
    except Exception:
        pass
    # If confidence column is legacy FLOAT, rebuild table with DOUBLE precision and integer hundredths column
    try:
        t = conn.execute(
            "SELECT data_type FROM information_schema.columns WHERE table_name = 'merchant_category_mapping' AND column_name = 'confidence'"
        ).fetchone()
        if t and isinstance(t[0], str) and t[0].upper() in ("FLOAT", "REAL"):
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """
                CREATE TABLE merchant_category_mapping_tmp AS
                SELECT 
                    id,
                    merchant_name,
                    merchant_pattern,
                    category_id,
                    CAST(COALESCE(confidence, 1.0) AS DOUBLE) AS confidence,
                    CAST(ROUND(COALESCE(confidence, 1.0) * 100) AS INTEGER) AS confidence_i,
                    usage_count,
                    last_used,
                    created_at
                FROM merchant_category_mapping
                """
            )
            conn.execute("DROP TABLE merchant_category_mapping")
            conn.execute(
                """
                CREATE TABLE merchant_category_mapping (
                    id TEXT PRIMARY KEY,
                    merchant_name TEXT NOT NULL,
                    merchant_pattern TEXT NOT NULL,
                    category_id TEXT NOT NULL,
                    confidence DOUBLE DEFAULT 1.0,
                    confidence_i INTEGER,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP,
                    UNIQUE(merchant_pattern, category_id)
                )
                """
            )
            conn.execute(
                "INSERT INTO merchant_category_mapping SELECT * FROM merchant_category_mapping_tmp"
            )
            conn.execute("DROP TABLE merchant_category_mapping_tmp")
            conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
    # Backfill integer hundredths confidence if missing
    try:
        conn.execute(
            "UPDATE merchant_category_mapping SET confidence_i = CAST(ROUND(COALESCE(confidence, 1.0) * 100) AS INTEGER) WHERE confidence_i IS NULL"
        )
    except Exception:
        pass

    # Phase 2: Merchant Intelligence Cache for LLM-derived classifications
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS merchant_intelligence_cache (
                id TEXT PRIMARY KEY,
                raw_description TEXT NOT NULL,
                description_hash TEXT NOT NULL,
                clean_merchant_name TEXT,
                recurring_type TEXT,
                sub_category TEXT,
                is_essential BOOLEAN,
                confidence DOUBLE DEFAULT 0.0,
                provider TEXT,
                model TEXT,
                latency_ms INTEGER,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0,
                last_hit_at TIMESTAMP,
                UNIQUE(description_hash)
            )
            """
        )
    except Exception:
        pass
    # Index for fast lookups by description hash
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mic_hash ON merchant_intelligence_cache(description_hash)")
    except Exception:
        pass
    # Add LLM-specific columns to recurring_series for Phase 2
    for sql in (
        "ALTER TABLE recurring_series ADD COLUMN llm_confidence DOUBLE",
        "ALTER TABLE recurring_series ADD COLUMN llm_provider TEXT",
        "ALTER TABLE recurring_series ADD COLUMN llm_classified_at TIMESTAMP",
    ):
        try:
            conn.execute(sql)
        except Exception:
            pass

    # Category normalization and deduplication (Phase 1 hardening)
    try:
        # Add normalized_name column if missing
        try:
            conn.execute("ALTER TABLE category ADD COLUMN normalized_name TEXT")
        except Exception:
            pass
        # Backfill normalized names
        try:
            conn.execute("UPDATE category SET normalized_name = lower(trim(name)) WHERE normalized_name IS NULL OR normalized_name = ''")
        except Exception:
            pass
        # Build canonical mapping and repoint transaction_category
        try:
            conn.execute("CREATE TEMP TABLE _cat_canon AS SELECT normalized_name, MIN(id) AS canonical_id FROM category GROUP BY normalized_name")
            conn.execute(
                """
                UPDATE transaction_category AS tc
                SET category_id = c2.canonical_id
                FROM _cat_canon c2
                JOIN category c ON c.id = tc.category_id
                WHERE c.normalized_name = c2.normalized_name
                  AND tc.category_id <> c2.canonical_id
                """
            )
            conn.execute("DELETE FROM category WHERE id NOT IN (SELECT canonical_id FROM _cat_canon)")
        except Exception:
            # ignore if temp table can't be created or already applied
            pass
        # Ensure uniqueness on normalized_name
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_category_normalized ON category(normalized_name)")
        except Exception:
            pass
    except Exception:
        # don't fail overall upgrade if normalization encounters issues
        pass


def _ensure_schema_version_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TIMESTAMP NOT NULL
        )
        """
    )
    # baseline if empty
    row = conn.execute("SELECT COUNT(1) FROM schema_version").fetchone()
    if not row or (row[0] == 0):
        from datetime import datetime as _dt, UTC as _UTC
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", [1, _dt.now(_UTC)])


def _run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    """Run pending SQL migrations from apps/backend/db/migrations (numeric order)."""
    try:
        from pathlib import Path
        # Compute repo root robustly: db.py is at apps/backend/src/ledgerloop/db.py
        p = Path(__file__).resolve()
        # expected parents: [ledgerloop, src, backend, apps, repo_root]
        repo_root = p.parents[4] if len(p.parents) >= 5 else p.parents[-1]
        mig_dir = repo_root / "apps" / "backend" / "db" / "migrations"
        if not mig_dir.exists():
            # Fallback to previous heuristic (parents[3]) in case of different layout
            alt_root = p.parents[3] if len(p.parents) >= 4 else repo_root
            alt = alt_root / "apps" / "backend" / "db" / "migrations"
            if alt.exists():
                mig_dir = alt
        mig_dir.mkdir(parents=True, exist_ok=True)
        # current version
        v = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 1
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
                conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, now())", [ver])
                v = ver
                continue
            # Run inside a transaction
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.execute(sql)
                conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, now())", [ver])
                conn.execute("COMMIT")
                v = ver
            except Exception:
                conn.execute("ROLLBACK")
                raise
    except Exception:
        # migrations are best-effort; do not crash app
        pass
