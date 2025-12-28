from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query

from ...db import get_conn
from ...p2p_detection import get_p2p_service


router = APIRouter(prefix="/p2p", tags=["p2p"])


@router.get("/summary")
def p2p_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    provider: Optional[str] = Query(None, description="Filter: venmo|cashapp|western_union|..."),
    counterparty: Optional[str] = Query(None, description="Case-insensitive substring match"),
    limit: int = Query(500, ge=1, le=5000),
):
    """Summarize P2P transactions grouped by provider + counterparty.

    P2P metadata is populated by `POST /api/detect/p2p?commit=true`.
    """
    conn = get_conn()
    where = ["t.p2p_provider IS NOT NULL"]
    params: list = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if provider:
        where.append("t.p2p_provider = ?")
        params.append(provider)
    if counterparty:
        where.append("lower(COALESCE(t.p2p_counterparty,'')) LIKE ?")
        params.append(f"%{counterparty.lower()}%")
    wh = " WHERE " + " AND ".join(where)

    rows = conn.execute(
        f"""
        SELECT
            t.p2p_provider AS provider,
            COALESCE(NULLIF(trim(t.p2p_counterparty), ''), '(unknown)') AS counterparty,
            COUNT(*) AS count,
            SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END) AS total_out,
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) AS total_in,
            SUM(t.amount) AS net,
            MIN(t.posted_at) AS first_date,
            MAX(t.posted_at) AS last_date
        FROM [transaction] t
        {wh}
        GROUP BY 1,2
        ORDER BY total_out DESC NULLS LAST, count DESC
        LIMIT ?
        """,
        params + [limit],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/transactions")
def p2p_transactions(
    provider: str = Query(..., description="zelle|venmo|cashapp|western_union|..."),
    counterparty: Optional[str] = Query(None, description="Exact counterparty (as shown in /summary). Use '(unknown)' to match NULLs."),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100000),
):
    """Drill down into the underlying transactions for one provider+counterparty row."""
    conn = get_conn()
    where = ["t.p2p_provider = ?"]
    params: list = [provider]
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if counterparty is not None:
        if counterparty == "(unknown)":
            where.append("(t.p2p_counterparty IS NULL OR trim(t.p2p_counterparty) = '')")
        else:
            where.append("t.p2p_counterparty = ?")
            params.append(counterparty)
    wh = " WHERE " + " AND ".join(where)

    rows = conn.execute(
        f"""
        SELECT
            t.id,
            t.posted_at,
            t.amount,
            t.currency,
            t.description_norm,
            t.p2p_direction,
            t.p2p_counterparty,
            t.account_id,
            COALESCE(c.name, NULL) AS category_name
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        LEFT JOIN category c ON c.id = tc.category_id
        {wh}
        ORDER BY t.posted_at DESC, abs(t.amount) DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


# ============================================================================
# NEW P2P Detection Service Endpoints (uses p2p_transaction table)
# ============================================================================

@router.post("/detect")
async def detect_p2p_transactions(
    background_tasks: BackgroundTasks,
    use_ai: bool = Query(False, description="Use AI for ambiguous transactions"),
    limit: int = Query(10000, ge=1, le=50000),
    skip_existing: bool = Query(True, description="Skip already-detected transactions"),
):
    """Run P2P detection on transactions.

    This endpoint detects P2P payments (Venmo, Zelle, CashApp, PayPal, Wire, Western Union)
    in your transactions and saves the results to the p2p_transaction table.

    - use_ai: Enable AI fallback for ambiguous transactions (slower but more thorough)
    - limit: Maximum transactions to process
    - skip_existing: If True, skip transactions that already have P2P detection results
    """
    service = get_p2p_service()

    # Run synchronously for smaller batches
    if limit <= 100:
        result = await service.detect_all_transactions(
            use_ai=use_ai,
            limit=limit,
            skip_existing=skip_existing,
        )
        return {"status": "completed", **result}

    # For larger batches, run in background
    async def run_detection():
        await service.detect_all_transactions(
            use_ai=use_ai,
            limit=limit,
            skip_existing=skip_existing,
        )

    background_tasks.add_task(run_detection)
    return {
        "status": "started",
        "message": f"P2P detection started for up to {limit} transactions",
    }


@router.get("/detected")
async def list_detected_p2p(
    service: Optional[str] = Query(None, description="Filter by service (venmo, zelle, cashapp, paypal, wire, western_union)"),
    counterparty: Optional[str] = Query(None, description="Filter by counterparty name (partial match)"),
    direction: Optional[str] = Query(None, description="Filter by direction (to, from)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List detected P2P transactions from the p2p_transaction table.

    This uses the new detection service results (separate from legacy p2p_* columns).
    """
    service_instance = get_p2p_service()
    transactions = service_instance.get_p2p_transactions(
        service=service,
        counterparty=counterparty,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    return {"transactions": transactions, "count": len(transactions)}


@router.get("/counterparties")
async def list_counterparties(
    recurring_only: bool = Query(False, description="Only return counterparties with recurring payments"),
    min_transactions: int = Query(1, ge=1, description="Minimum transaction count"),
    limit: int = Query(50, ge=1, le=500),
):
    """List all counterparties (people you've transacted with via P2P).

    Returns counterparty information including:
    - Total amount sent/received
    - Transaction count
    - First/last transaction dates
    - Known aliases (different spellings of the same person's name)
    """
    service = get_p2p_service()
    counterparties = service.get_counterparties(
        recurring_only=recurring_only,
        min_transactions=min_transactions,
        limit=limit,
    )
    return {
        "counterparties": [
            {
                "id": cp.id,
                "name": cp.name_normalized,
                "aliases": cp.aliases,
                "total_sent": cp.total_sent,
                "total_received": cp.total_received,
                "net_flow": cp.total_received - cp.total_sent,
                "transaction_count": cp.transaction_count,
                "first_seen": cp.first_seen,
                "last_seen": cp.last_seen,
                "is_recurring": cp.is_recurring,
                "counterparty_type": cp.counterparty_type,
            }
            for cp in counterparties
        ],
        "count": len(counterparties),
    }


@router.get("/counterparties/{counterparty_id}/transactions")
async def get_counterparty_transactions(counterparty_id: str):
    """Get all P2P transactions with a specific counterparty."""
    service = get_p2p_service()
    transactions = service.get_counterparty_transactions(counterparty_id)
    return {"transactions": transactions, "count": len(transactions)}


@router.get("/stats")
async def get_p2p_stats():
    """Get P2P transaction statistics.

    Returns:
    - Total P2P transactions detected
    - Breakdown by service (Venmo, Zelle, CashApp, PayPal, Wire, Western Union)
    - Breakdown by direction (sent vs received)
    - Top counterparties by transaction count
    """
    service = get_p2p_service()
    return service.get_stats()


@router.post("/merge-counterparties")
async def merge_counterparties(source_id: str, target_id: str):
    """Merge two counterparties (for user-corrected matching).

    When the system incorrectly identifies the same person as two different
    counterparties, use this endpoint to merge them.

    - source_id: Counterparty to merge from (will be deleted)
    - target_id: Counterparty to merge into (will be updated)

    All transactions from source will be associated with target.
    Source's name will become an alias of target.
    """
    service = get_p2p_service()
    success = service.merge_counterparties(source_id, target_id)

    if success:
        return {"status": "success", "message": f"Merged {source_id} into {target_id}"}
    else:
        return {"status": "error", "message": "One or both counterparties not found"}


@router.post("/analyze-single")
async def analyze_single_transaction(tx_id: str, use_ai: bool = False):
    """Analyze a single transaction for P2P patterns.

    Useful for testing detection on specific transactions.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id, description_norm, amount FROM [transaction] WHERE id = ?",
        [tx_id],
    ).fetchone()

    if not row:
        return {"status": "error", "message": "Transaction not found"}

    tx = {"description_norm": row[1], "amount": row[2]}
    service = get_p2p_service()

    # Try heuristic detection
    result = service.detect_p2p_transaction(tx)

    if result:
        # Save and return
        p2p_id = service.save_p2p_transaction(tx_id, result)
        return {
            "status": "detected",
            "detection_method": "heuristic",
            "p2p_id": p2p_id,
            "service": result.service,
            "counterparty": result.counterparty_raw,
            "direction": result.direction,
            "confidence": result.confidence,
        }

    # Try AI if requested
    if use_ai:
        result = await service.analyze_with_ai(tx)
        if result:
            p2p_id = service.save_p2p_transaction(tx_id, result)
            return {
                "status": "detected",
                "detection_method": "ai",
                "p2p_id": p2p_id,
                "service": result.service,
                "counterparty": result.counterparty_raw,
                "direction": result.direction,
                "confidence": result.confidence,
            }

    return {"status": "not_detected", "message": "Transaction does not appear to be P2P"}


# ============================================================================
# AI ENRICHMENT ENDPOINTS
# ============================================================================

@router.post("/enrich")
async def enrich_p2p_transactions(
    service_filter: Optional[str] = Query(None, description="Only enrich transactions from this service (e.g., 'paypal')"),
    only_unclassified: bool = Query(True, description="Only enrich transactions without classification"),
    limit: int = Query(50, ge=1, le=500),
):
    """Enrich P2P transactions with AI classification.

    This uses AI to classify P2P transactions into:
    - Transaction type: p2p_transfer, subscription, or purchase
    - Counterparty type: person or business
    - Merchant category (if business)
    - Whether it's recurring

    This helps distinguish true P2P transfers from PayPal purchases and subscriptions.
    """
    service = get_p2p_service()
    result = await service.enrich_all_p2p(
        service_filter=service_filter,
        only_unclassified=only_unclassified,
        limit=limit,
    )
    return {"status": "completed", **result}


@router.post("/enrich/{p2p_id}")
async def enrich_single_p2p(p2p_id: str):
    """Enrich a single P2P transaction with AI classification."""
    service = get_p2p_service()
    return await service.enrich_with_ai(p2p_id)


@router.get("/enrichment-stats")
async def get_enrichment_stats():
    """Get P2P enrichment statistics.

    Returns breakdown by:
    - Transaction type (p2p_transfer, subscription, purchase)
    - Counterparty type (person, business)
    - Enrichment status (how many have been AI-enriched)
    - Service-by-type breakdown
    """
    service = get_p2p_service()
    return service.get_enrichment_stats()


@router.get("/unlinked-recurring")
async def get_unlinked_recurring():
    """Get P2P transactions that appear recurring but aren't linked to the recurring workflow.

    This helps identify transactions that should be tracked in the recurring system
    to avoid double-counting.
    """
    service = get_p2p_service()
    return {"candidates": service.get_unlinked_recurring_p2p()}


@router.post("/link-recurring")
async def link_to_recurring(p2p_id: str, recurring_series_id: str):
    """Link a P2P transaction to a recurring series.

    This coordinates P2P detection with the recurring workflow to prevent double-counting.
    """
    service = get_p2p_service()
    success = service.link_to_recurring(p2p_id, recurring_series_id)
    if success:
        return {"status": "success", "message": f"Linked P2P {p2p_id} to recurring series {recurring_series_id}"}
    return {"status": "error", "message": "Failed to link"}


