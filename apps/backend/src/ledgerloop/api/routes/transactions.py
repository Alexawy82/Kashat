from __future__ import annotations

from datetime import date, datetime, UTC
import uuid
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_conn


router = APIRouter(prefix="/transactions", tags=["transactions"])


class AssignCategoryBody(BaseModel):
    category_id: str


class TransactionItem(BaseModel):
    id: str
    account_id: str
    posted_at: date
    amount: float
    currency: str | None = None
    description_norm: str
    payee: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    is_transfer: bool
    is_business: bool
    is_income: bool
    is_adjustment: bool
    zelle_direction: str | None = None
    zelle_counterparty: str | None = None
    ai_merchant_name: str | None = None
    ai_category_suggestions: str | None = None
    ai_confidence_score: float | None = None
    ai_processed_at: datetime | None = None


@router.get("")
def list_transactions(
    account_id: Optional[str] = None,
    start_date: Optional[date] = Query(None, description="Inclusive start date"),
    end_date: Optional[date] = Query(None, description="Inclusive end date"),
    category_id: Optional[str] = Query(None),
    include_transfers: bool = Query(False),
    is_business: Optional[bool] = Query(None),
    desc: Optional[str] = Query(None, description="Case-insensitive substring in description"),
    sort_by: str = Query("posted_at", description="posted_at|amount|description|category|business|income|adjustment"),
    sort_dir: str = Query("desc", description="asc|desc"),
    limit: int = 100,
    offset: int = 0,
):
    conn = get_conn()
    where = []
    params = []
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if category_id:
        where.append("tc.category_id = ?")
        params.append(category_id)
    if is_business is not None:
        where.append("t.is_business = ?")
        params.append(is_business)
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")
    if desc:
        where.append("lower(t.description_norm) LIKE ?")
        params.append(f"%{desc.lower()}%")
    wh = " WHERE " + " AND ".join(where) if where else ""
    # Sorting
    sort_map = {
        "posted_at": "t.posted_at",
        "amount": "t.amount",
        "description": "COALESCE(t.payee_alias, t.description_norm)",
        "category": "c.name",
        "business": "t.is_business",
        "income": "t.is_income",
        "adjustment": "t.is_adjustment",
    }
    col = sort_map.get(sort_by, "t.posted_at")
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    rows = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               COALESCE(t.payee_alias, t.description_norm) AS payee,
               tc.category_id, c.name as category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer
               , t.is_business, t.is_income, t.is_adjustment, t.zelle_direction, t.zelle_counterparty
               , t.ai_merchant_name, t.ai_category_suggestions, t.ai_confidence_score, t.ai_processed_at
        FROM transaction t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        ORDER BY {col} {direction}
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()
    columns = [x[0] for x in conn.description]
    items = [dict(zip(columns, r)) for r in rows]
    # Cast to model for consistency and future validation
    return [TransactionItem(**i) for i in items]


class PatchTxBody(BaseModel):
    is_business: Optional[bool] = None
    is_adjustment: Optional[bool] = None
    is_income: Optional[bool] = None


@router.patch("/{tx_id}")
def patch_transaction(tx_id: str, body: PatchTxBody):
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM transaction WHERE id = ?", [tx_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="transaction not found")
    sets = []
    params = []
    if body.is_business is not None:
        sets.append("is_business = ?")
        params.append(body.is_business)
    if body.is_adjustment is not None:
        sets.append("is_adjustment = ?")
        params.append(body.is_adjustment)
    if body.is_income is not None:
        sets.append("is_income = ?")
        params.append(body.is_income)
    if not sets:
        return {"updated": 0}
    import json as _json
    from datetime import datetime as _dt
    conn.execute(f"UPDATE transaction SET {', '.join(sets)} WHERE id = ?", params + [tx_id])
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transaction", tx_id, "patch", _json.dumps(body.dict(exclude_none=True)), _dt.utcnow(), "user"],
    )
    return {"updated": 1}


@router.post("/{tx_id}/category")
def assign_category(tx_id: str, body: AssignCategoryBody):
    conn = get_conn()
    # verify tx exists
    exists = conn.execute("SELECT 1 FROM transaction WHERE id = ?", [tx_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="transaction not found")
    # verify category exists
    cat = conn.execute("SELECT 1 FROM category WHERE id = ?", [body.category_id]).fetchone()
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
    conn.execute(
        "INSERT INTO transaction_category (tx_id, category_id, applied_by) VALUES (?, ?, ?)",
        [tx_id, body.category_id, "manual"],
    )
    import json as _json
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            str(uuid.uuid4()),
            "transaction",
            tx_id,
            "manual_category",
            _json.dumps({"category_id": body.category_id}),
            datetime.now(UTC),
            "user",
        ],
    )
    return {"tx_id": tx_id, "category_id": body.category_id}


@router.delete("/{tx_id}")
def delete_transaction(tx_id: str):
    """Delete a transaction and related references (categories, tags, transfer links)."""
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM transaction WHERE id = ?", [tx_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="transaction not found")
    # delete references
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction_tag WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM match_transfer WHERE left_tx_id = ? OR right_tx_id = ?", [tx_id, tx_id])
    conn.execute("DELETE FROM recurring_tx WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction_ingest WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction WHERE id = ?", [tx_id])
    import json as _json
    from datetime import datetime as _dt, UTC as _UTC
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transaction", tx_id, "delete", _json.dumps({}), _dt.now(_UTC), "user"],
    )
    return {"deleted": tx_id}


@router.get("/{tx_id}/ai-details")
def get_ai_details(tx_id: str) -> dict:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, description_norm, ai_merchant_name, ai_category_suggestions,
               ai_confidence_score, ai_provider, ai_model, ai_latency_ms
        FROM transaction WHERE id = ?
        """,
        [tx_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="transaction not found")
    cols = [c[0] for c in conn.description]
    data = dict(zip(cols, row))
    return {"transaction": data}
