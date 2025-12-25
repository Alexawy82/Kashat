from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from ...db import get_conn


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
