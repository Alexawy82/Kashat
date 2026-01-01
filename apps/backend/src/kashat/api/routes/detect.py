from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query
from typing import Optional

from ...db import get_conn
from ...detect.zelle import parse_zelle_descriptor
from ...detect.income import mark_income
from ...detect.adjustments import mark_adjustments
from ...detect.p2p import parse_p2p_descriptor


router = APIRouter(prefix="/detect", tags=["detect"])


@router.post("/full-pipeline")
async def run_full_detection_pipeline(
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = Query(None, description="Account ID to process (optional, defaults to all)"),
):
    """Run the FULL detection pipeline including dedup, recurring, merge, and cancellation detection.

    Pipeline order:
    1. Zelle tagging
    2. Income detection
    3. Adjustments detection
    4. Transaction Deduplication (AI)
    5. Transfer detection
    6. P2P detection
    7. Recurring detection
    8. Merge duplicate series (e.g., Google Fiber variants)
    9. Cancellation detection

    This is the same pipeline that runs automatically after imports.
    Use this to manually re-run detection on existing transactions.
    """
    from .imports import _run_builtin_detectors

    conn = get_conn()

    # If no account specified, get all accounts
    if account_id:
        account_ids = [account_id]
    else:
        rows = conn.execute("SELECT DISTINCT id FROM account").fetchall()
        account_ids = [r[0] for r in rows]

    # Run in background for each account
    for acc_id in account_ids:
        background_tasks.add_task(_run_builtin_detectors, acc_id)

    return {
        "status": "queued",
        "accounts": len(account_ids),
        "message": f"Full detection pipeline queued for {len(account_ids)} account(s)"
    }


@router.post("/subscription-workflow")
async def run_subscription_workflow(
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = Query(None),
):
    """Run subscription/recurring specific workflow:

    1. Recurring detection (find new patterns)
    2. Merge duplicate merchants (consolidate e.g., 'Google Fiber' variants)
    3. Auto-link transactions to existing series
    4. Update series status (detect cancellations)

    Use this to refresh recurring detection and merge duplicates.
    """
    conn = get_conn()

    async def _run_subscription_workflow():
        try:
            # 1. Recurring detection
            from ...recurring import suggest_recurring, merge_duplicate_merchants, calculate_series_status, auto_link_transactions_to_series

            suggest_result = suggest_recurring(min_occurrences=3)
            recurring_count = len(suggest_result.get("candidates", []))
            print(f"Recurring detection: found {recurring_count} candidates")

            # 2. Merge duplicate merchants
            merge_result = merge_duplicate_merchants(conn)
            merged_count = merge_result.get("merged", 0)
            print(f"Series merge: {merged_count} duplicate series merged")

            # 3. Auto-link transactions to series
            link_result = auto_link_transactions_to_series()
            linked_count = link_result.get("linked_transactions", 0)
            print(f"Auto-link: {linked_count} transactions linked to series")

            # 4. Update series status (cancellation detection)
            series_rows = conn.execute("""
                SELECT id, last_date, next_date, cadence
                FROM recurring_series
                WHERE status = 'confirmed'
            """).fetchall()

            cancelled_count = 0
            for series_id, last_date, next_date, cadence in series_rows:
                try:
                    status_info = calculate_series_status(last_date, next_date, cadence)
                    if status_info.get("status") == "likely_cancelled":
                        conn.execute("""
                            UPDATE recurring_series
                            SET health_status = 'likely_cancelled', health_score = ?
                            WHERE id = ?
                        """, [status_info.get("health_score", 0.1), series_id])
                        cancelled_count += 1
                except Exception:
                    pass

            print(f"Cancellation detection: {cancelled_count} series marked as likely cancelled")

            return {
                "recurring_candidates": recurring_count,
                "series_merged": merged_count,
                "transactions_linked": linked_count,
                "likely_cancelled": cancelled_count
            }
        except Exception as e:
            print(f"Subscription workflow error: {e}")
            return {"error": str(e)}

    background_tasks.add_task(_run_subscription_workflow)

    return {
        "status": "queued",
        "message": "Subscription workflow queued"
    }


@router.post("/dedup")
async def run_deduplication(
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = Query(None),
    days_window: int = Query(14, description="Days to look back for duplicates"),
    auto_merge_threshold: float = Query(0.92, description="Confidence threshold for auto-merge"),
):
    """Run intelligent duplicate detection and optional auto-merge.

    Detects duplicate transactions using AI similarity analysis.
    Auto-merges only high-confidence duplicates (default >= 0.92).
    """
    async def _run_dedup():
        try:
            from ...ai_intelligent_dedup import get_intelligent_dedup_detector

            dedup_detector = get_intelligent_dedup_detector()
            duplicates = await dedup_detector.detect_duplicates(
                account_id=account_id,
                days_window=days_window,
                batch_size=1000
            )

            if duplicates:
                resolve_result = await dedup_detector.auto_resolve_duplicates(
                    duplicates,
                    auto_merge_threshold=auto_merge_threshold
                )
                print(f"Dedup: {len(duplicates)} candidates, {resolve_result.get('auto_merged', 0)} auto-merged")
                return {
                    "candidates": len(duplicates),
                    "auto_merged": resolve_result.get("auto_merged", 0),
                    "review_required": resolve_result.get("reviewed_required", 0)
                }
            return {"candidates": 0, "auto_merged": 0}
        except Exception as e:
            print(f"Dedup error: {e}")
            return {"error": str(e)}

    background_tasks.add_task(_run_dedup)

    return {
        "status": "queued",
        "message": f"Deduplication queued (days_window={days_window}, threshold={auto_merge_threshold})"
    }


@router.post("/merge-duplicate-series")
async def merge_duplicate_series():
    """Merge duplicate recurring series (e.g., 'Google Fiber' variants).

    Consolidates series that have the same AI-extracted merchant name and cadence.
    Keeps the best series and moves all transactions to it.
    """
    from ...recurring import merge_duplicate_merchants
    conn = get_conn()
    result = merge_duplicate_merchants(conn)
    return {
        "status": "completed",
        "merged": result.get("merged", 0),
        "details": result.get("details", [])
    }


@router.post("/cancellations")
async def detect_cancellations(
    auto_update: bool = Query(False, description="Auto-update series status in database"),
):
    """Detect recurring services that appear to have been cancelled.

    Checks all confirmed series for missed payments and marks likely cancellations.

    Args:
        auto_update: If True, updates health_status in database. If False, just reports.
    """
    from ...recurring import calculate_series_status
    conn = get_conn()

    series_rows = conn.execute("""
        SELECT id, name, display_name, last_date, next_date, cadence, amount_mean
        FROM recurring_series
        WHERE status = 'confirmed'
    """).fetchall()

    likely_cancelled = []
    for series_id, name, display_name, last_date, next_date, cadence, amount in series_rows:
        try:
            status_info = calculate_series_status(last_date, next_date, cadence)
            if status_info.get("status") == "likely_cancelled":
                likely_cancelled.append({
                    "series_id": series_id,
                    "name": display_name or name,
                    "last_date": last_date,
                    "cadence": cadence,
                    "amount": float(amount) if amount else 0,
                    "missed_payments": status_info.get("missed_payments", 0),
                    "health_score": status_info.get("health_score", 0)
                })

                if auto_update:
                    conn.execute("""
                        UPDATE recurring_series
                        SET health_status = 'likely_cancelled', health_score = ?
                        WHERE id = ?
                    """, [status_info.get("health_score", 0.1), series_id])
        except Exception:
            pass

    return {
        "status": "completed",
        "likely_cancelled_count": len(likely_cancelled),
        "auto_updated": auto_update,
        "series": likely_cancelled
    }


@router.post("/refresh-next-dates")
async def refresh_next_dates():
    """Recalculate next_date for all recurring series based on last_date and cadence.

    This fixes the calendar view when next_date values are stale.
    """
    from datetime import date, timedelta
    conn = get_conn()

    cadence_days = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30,
        'quarterly': 91,
        'semiannual': 182,
        'semi_annual': 182,
        'annual': 365,
    }

    # Get all series with last_date
    rows = conn.execute("""
        SELECT id, name, last_date, cadence, next_date
        FROM recurring_series
        WHERE status IN ('pending', 'confirmed')
          AND last_date IS NOT NULL
    """).fetchall()

    updated = 0
    today = date.today()

    for series_id, name, last_date_str, cadence, current_next in rows:
        try:
            # Parse last_date
            if not last_date_str:
                continue
            last_date = date.fromisoformat(last_date_str[:10])
            interval = cadence_days.get(cadence, 30)

            # Calculate next_date by projecting forward from last_date
            next_date = last_date + timedelta(days=interval)

            # Keep advancing until we get to a future date
            while next_date < today:
                next_date += timedelta(days=interval)

            next_date_str = next_date.isoformat()

            # Update if different
            if next_date_str != current_next:
                conn.execute("""
                    UPDATE recurring_series
                    SET next_date = ?
                    WHERE id = ?
                """, [next_date_str, series_id])
                updated += 1
                print(f"Updated {name}: {current_next} -> {next_date_str}")

        except Exception as e:
            print(f"Error updating {name}: {e}")

    return {
        "status": "completed",
        "updated": updated,
        "total_checked": len(rows)
    }


@router.post("/fix-p2p-classification")
async def fix_p2p_classification():
    """Remove P2P services (Zelle, Cash App, Venmo, etc.) from recurring series.

    These shouldn't be treated as recurring bills since they're payment methods,
    not actual subscriptions or bills.
    """
    conn = get_conn()

    p2p_patterns = [
        'zelle', 'cash app', 'cashapp', 'venmo', 'paypal',
        'western union', 'wu send', 'moneygram'
    ]

    # Find series that match P2P patterns
    pattern_clause = ' OR '.join(['LOWER(name) LIKE ?' for _ in p2p_patterns])
    params = [f'%{p}%' for p in p2p_patterns]

    rows = conn.execute(f"""
        SELECT id, name, display_name, recurring_type
        FROM recurring_series
        WHERE ({pattern_clause})
          AND status IN ('pending', 'confirmed')
    """, params).fetchall()

    removed = []
    for series_id, name, display_name, rec_type in rows:
        # Mark as rejected instead of deleting (safer)
        conn.execute("""
            UPDATE recurring_series
            SET status = 'rejected', decided_at = datetime('now')
            WHERE id = ?
        """, [series_id])
        removed.append({
            "id": series_id,
            "name": display_name or name,
            "was_type": rec_type
        })

    return {
        "status": "completed",
        "removed_count": len(removed),
        "removed": removed
    }


@router.post("/zelle")
def detect_zelle(commit: bool = False):
    conn = get_conn()
    rows = conn.execute("SELECT id, description_norm FROM [transaction]").fetchall()
    if not commit:
        # Preview only: count matches
        count = 0
        for tx_id, desc in rows:
            info = parse_zelle_descriptor(desc or "")
            if info:
                count += 1
        return {"matched": count, "committed": False}

    # Commit path: update tags and fields
    tagged = 0
    for tx_id, desc in rows:
        info = parse_zelle_descriptor(desc or "")
        if not info:
            continue
        conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, "zelle"])
        if info.get("direction") == "from":
            conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, "zelle_from"])
        elif info.get("direction") == "to":
            conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, "zelle_to"])
        if info.get("direction") in ("from", "to"):
            conn.execute("UPDATE [transaction] SET zelle_direction = ? WHERE id = ?", [info["direction"], tx_id])
        if info.get("counterparty"):
            conn.execute("UPDATE [transaction] SET zelle_counterparty = ? WHERE id = ?", [info["counterparty"], tx_id])
        tagged += 1
    return {"tagged": tagged, "committed": True}


@router.post("/auto")
def run_all_detectors():
    """Run all built-in detectors and persist results.

    - Zelle direction/counterparty tagging
    - Income marking (commit)
    - Adjustments marking (commit)
    """
    z = detect_zelle(commit=True)
    p2p = detect_p2p(commit=True)
    inc = detect_income(commit=True)
    adj = detect_adjustments(commit=True)
    return {"zelle": z, "p2p": p2p, "income": inc, "adjustments": adj}


@router.post("/income")
def detect_income(commit: bool = False):
    conn = get_conn()
    rows = conn.execute("SELECT id, posted_at, amount, description_norm FROM [transaction]").fetchall()
    records = [
        {"id": r[0], "posted_at": r[1], "amount": r[2], "description_norm": r[3]}
        for r in rows
    ]
    ids = mark_income(records)
    if commit:
        for tx_id in ids:
            conn.execute("UPDATE [transaction] SET is_income = TRUE WHERE id = ?", [tx_id])
    return {"matched": len(ids), "committed": bool(commit)}


@router.post("/adjustments")
def detect_adjustments(commit: bool = False):
    conn = get_conn()
    rows = conn.execute("SELECT id, posted_at, amount, description_norm FROM [transaction]").fetchall()
    records = [
        {"id": r[0], "posted_at": r[1], "amount": r[2], "description_norm": r[3]}
        for r in rows
    ]
    ids = mark_adjustments(records)
    if commit:
        for tx_id in ids:
            conn.execute("UPDATE [transaction] SET is_adjustment = TRUE WHERE id = ?", [tx_id])
    return {"matched": len(ids), "committed": bool(commit)}


@router.post("/p2p")
def detect_p2p(commit: bool = False):
    """Detect and (optionally) tag P2P transfers like Venmo/Cash App/Western Union."""
    conn = get_conn()
    rows = conn.execute("SELECT id, amount, description_norm FROM [transaction]").fetchall()
    if not commit:
        matched = 0
        for tx_id, amount, desc in rows:
            info = parse_p2p_descriptor(desc or "", float(amount) if amount is not None else None)
            if info:
                matched += 1
        return {"matched": matched, "committed": False}

    tagged = 0
    for tx_id, amount, desc in rows:
        info = parse_p2p_descriptor(desc or "", float(amount) if amount is not None else None)
        if not info:
            continue
        provider = info.get("provider")
        direction = info.get("direction")
        counterparty = info.get("counterparty")
        # tags
        conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, "p2p"])
        if provider:
            conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, f"p2p_{provider}"])
        if direction in ("to", "from"):
            conn.execute("INSERT INTO transaction_tag (tx_id, tag) VALUES (?, ?) ON CONFLICT DO NOTHING", [tx_id, f"p2p_{direction}"])
        # structured columns
        conn.execute("UPDATE [transaction] SET p2p_provider = ? WHERE id = ?", [provider, tx_id])
        conn.execute("UPDATE [transaction] SET p2p_direction = ? WHERE id = ?", [direction, tx_id])
        if counterparty:
            conn.execute("UPDATE [transaction] SET p2p_counterparty = ? WHERE id = ?", [counterparty, tx_id])
        tagged += 1
    return {"tagged": tagged, "committed": True}
