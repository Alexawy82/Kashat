from __future__ import annotations

from fastapi import APIRouter
from typing import List, Dict, Any

from ...db import get_conn


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts() -> List[Dict[str, Any]]:
    """List accounts with basic info and transaction counts."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT a.id, a.name, a.type, a.last4, a.currency,
               COUNT(t.id) AS transaction_count,
               MIN(t.posted_at) AS first_tx_date,
               MAX(t.posted_at) AS last_tx_date
        FROM account a
        LEFT JOIN [transaction] t ON t.account_id = a.id
        GROUP BY a.id, a.name, a.type, a.last4, a.currency
        ORDER BY a.name
        """
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]

