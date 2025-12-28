"""
Enhanced Prometheus Metrics for LedgerLoop.

Provides comprehensive monitoring capabilities including:
- HTTP request metrics (requests, latency, errors)
- Business metrics (transactions, categories, AI usage)
- Database metrics (connection status, query counts)
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
import time
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# HTTP REQUEST METRICS
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "route"]
)

HTTP_ERRORS_TOTAL = Counter(
    "http_errors_total",
    "Total HTTP errors by type",
    ["method", "route", "error_type"]
)

# =============================================================================
# BUSINESS METRICS - TRANSACTIONS
# =============================================================================

TRANSACTIONS_TOTAL = Gauge(
    "transactions_total",
    "Total number of transactions in the database"
)

TRANSACTIONS_IMPORTED = Counter(
    "transactions_imported_total",
    "Total number of transactions imported",
    ["source"]  # csv, pdf, api
)

TRANSACTIONS_CATEGORIZED = Gauge(
    "transactions_categorized",
    "Number of transactions with categories assigned"
)

TRANSACTIONS_UNCATEGORIZED = Gauge(
    "transactions_uncategorized",
    "Number of transactions without categories"
)

TRANSACTIONS_BY_CATEGORY = Gauge(
    "transactions_by_category",
    "Number of transactions per category",
    ["category_id", "category_name"]
)

# =============================================================================
# BUSINESS METRICS - AI
# =============================================================================

AI_CATEGORIZATIONS_TOTAL = Counter(
    "ai_categorizations_total",
    "Total AI categorization attempts",
    ["status"]  # success, failed, skipped
)

AI_RESPONSE_TIME = Histogram(
    "ai_response_time_seconds",
    "AI processing response time in seconds",
    ["operation"],  # categorize, enhance, suggest
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

AI_CONFIDENCE_SCORE = Histogram(
    "ai_confidence_score",
    "Distribution of AI confidence scores",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

AI_JOBS_IN_PROGRESS = Gauge(
    "ai_jobs_in_progress",
    "Number of AI jobs currently processing"
)

# =============================================================================
# BUSINESS METRICS - IMPORTS
# =============================================================================

IMPORT_RUNS_TOTAL = Gauge(
    "import_runs_total",
    "Total number of import runs"
)

IMPORT_FILES_PROCESSED = Counter(
    "import_files_processed_total",
    "Total files processed",
    ["file_type", "status"]  # csv/pdf, success/failed/duplicate
)

IMPORT_DUPLICATES_DETECTED = Counter(
    "import_duplicates_detected_total",
    "Number of duplicate transactions detected during import"
)

# =============================================================================
# BUSINESS METRICS - TRANSFERS & RECURRING
# =============================================================================

TRANSFERS_DETECTED = Gauge(
    "transfers_detected",
    "Number of detected internal transfers"
)

TRANSFERS_CONFIRMED = Gauge(
    "transfers_confirmed",
    "Number of confirmed transfers"
)

RECURRING_SERIES_TOTAL = Gauge(
    "recurring_series_total",
    "Total number of recurring transaction series"
)

RECURRING_SERIES_CONFIRMED = Gauge(
    "recurring_series_confirmed",
    "Number of confirmed recurring series"
)

# =============================================================================
# DATABASE METRICS
# =============================================================================

DB_CONNECTION_STATUS = Gauge(
    "db_connection_status",
    "Database connection status (1 = connected, 0 = disconnected)"
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

DB_QUERIES_TOTAL = Counter(
    "db_queries_total",
    "Total database queries",
    ["query_type"]
)

# =============================================================================
# RULES ENGINE METRICS
# =============================================================================

RULES_TOTAL = Gauge(
    "rules_total",
    "Total number of categorization rules"
)

RULES_APPLIED_TOTAL = Counter(
    "rules_applied_total",
    "Total number of rule applications",
    ["rule_id", "action_type"]
)

RULES_MATCHES_TOTAL = Counter(
    "rules_matches_total",
    "Total rule matches",
    ["rule_id"]
)

# =============================================================================
# APPLICATION INFO
# =============================================================================

APP_INFO = Info(
    "ledgerloop_app",
    "LedgerLoop application information"
)

# Set app info once
APP_INFO.info({
    "version": "1.0.0",
    "environment": "development"
})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def record_request_metrics(method: str, route: str, status: int, duration: float):
    """Record HTTP request metrics."""
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, route=route).observe(duration)

    if status >= 400:
        error_type = "client_error" if status < 500 else "server_error"
        HTTP_ERRORS_TOTAL.labels(method=method, route=route, error_type=error_type).inc()


def record_transaction_import(source: str, count: int):
    """Record transaction import metrics."""
    TRANSACTIONS_IMPORTED.labels(source=source).inc(count)


def record_ai_categorization(status: str, duration: Optional[float] = None, confidence: Optional[float] = None):
    """Record AI categorization metrics."""
    AI_CATEGORIZATIONS_TOTAL.labels(status=status).inc()

    if duration is not None:
        AI_RESPONSE_TIME.labels(operation="categorize").observe(duration)

    if confidence is not None:
        AI_CONFIDENCE_SCORE.observe(confidence)


def record_import_file(file_type: str, status: str):
    """Record import file processing metrics."""
    IMPORT_FILES_PROCESSED.labels(file_type=file_type, status=status).inc()


def record_duplicate_detected():
    """Record duplicate transaction detection."""
    IMPORT_DUPLICATES_DETECTED.inc()


@contextmanager
def track_ai_job():
    """Context manager to track AI job progress."""
    AI_JOBS_IN_PROGRESS.inc()
    try:
        yield
    finally:
        AI_JOBS_IN_PROGRESS.dec()


@contextmanager
def track_request_in_progress(method: str, route: str):
    """Context manager to track in-progress requests."""
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).inc()
    try:
        yield
    finally:
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, route=route).dec()


def time_ai_operation(operation: str):
    """Decorator to time AI operations."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                AI_RESPONSE_TIME.labels(operation=operation).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                AI_RESPONSE_TIME.labels(operation=operation).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def update_database_metrics():
    """Update database-related gauge metrics from database state."""
    try:
        from .db import get_conn
        conn = get_conn()

        # Mark DB as connected
        DB_CONNECTION_STATUS.set(1)

        # Total transactions
        result = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()
        TRANSACTIONS_TOTAL.set(result[0] if result else 0)

        # Categorized vs uncategorized
        result = conn.execute("""
            SELECT
                COUNT(DISTINCT tc.tx_id) as categorized,
                COUNT(t.id) - COUNT(DISTINCT tc.tx_id) as uncategorized
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        """).fetchone()
        if result:
            TRANSACTIONS_CATEGORIZED.set(result[0])
            TRANSACTIONS_UNCATEGORIZED.set(result[1])

        # Import runs
        result = conn.execute("SELECT COUNT(*) FROM import_run").fetchone()
        IMPORT_RUNS_TOTAL.set(result[0] if result else 0)

        # Rules
        try:
            result = conn.execute("SELECT COUNT(*) FROM rule WHERE enabled = true").fetchone()
            RULES_TOTAL.set(result[0] if result else 0)
        except Exception:
            pass

        # Transfers
        try:
            result = conn.execute("SELECT COUNT(*) FROM match_transfer WHERE decided_at IS NULL").fetchone()
            TRANSFERS_DETECTED.set(result[0] if result else 0)

            result = conn.execute("SELECT COUNT(*) FROM match_transfer WHERE decided_at IS NOT NULL AND rejected = false").fetchone()
            TRANSFERS_CONFIRMED.set(result[0] if result else 0)
        except Exception:
            pass

        # Recurring
        try:
            result = conn.execute("SELECT COUNT(DISTINCT series_id) FROM recurring_tx").fetchone()
            RECURRING_SERIES_TOTAL.set(result[0] if result else 0)

            result = conn.execute("""
                SELECT COUNT(DISTINCT series_id) FROM recurring_tx rt
                JOIN recurring_series rs ON rt.series_id = rs.id
                WHERE rs.confirmed_at IS NOT NULL
            """).fetchone()
            RECURRING_SERIES_CONFIRMED.set(result[0] if result else 0)
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Failed to update database metrics: {e}")
        DB_CONNECTION_STATUS.set(0)


def get_metrics_snapshot() -> dict:
    """Get a snapshot of current metrics as a dictionary (for JSON endpoints)."""
    try:
        from .db import get_conn
        conn = get_conn()

        # Get counts
        tx_total = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]

        categorized_result = conn.execute("""
            SELECT COUNT(DISTINCT tx_id) FROM transaction_category
        """).fetchone()
        tx_categorized = categorized_result[0] if categorized_result else 0

        import_result = conn.execute("SELECT COUNT(*) FROM import_run").fetchone()
        import_runs = import_result[0] if import_result else 0

        return {
            "transactions": {
                "total": tx_total,
                "categorized": tx_categorized,
                "uncategorized": tx_total - tx_categorized,
                "categorization_rate": round(tx_categorized / tx_total * 100, 1) if tx_total > 0 else 0
            },
            "imports": {
                "total_runs": import_runs
            }
        }
    except Exception as e:
        logger.warning(f"Failed to get metrics snapshot: {e}")
        return {"error": str(e)}
