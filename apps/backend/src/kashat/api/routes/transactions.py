from __future__ import annotations

import logging
from datetime import date, datetime, UTC
import uuid
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_conn

logger = logging.getLogger(__name__)


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
    p2p_provider: str | None = None
    p2p_direction: str | None = None
    p2p_counterparty: str | None = None
    ai_merchant_name: str | None = None
    ai_category_suggestions: str | None = None
    ai_confidence_score: float | None = None
    ai_processed_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None


@router.get("")
def list_transactions(
    account_id: Optional[str] = None,
    start_date: Optional[date] = Query(None, description="Inclusive start date"),
    end_date: Optional[date] = Query(None, description="Inclusive end date"),
    category_id: Optional[str] = Query(None),
    uncategorized: bool = Query(False, description="Only transactions without a category"),
    include_transfers: bool = Query(False),
    is_business: Optional[bool] = Query(None),
    is_income: Optional[bool] = Query(None),
    desc: Optional[str] = Query(None, description="Case-insensitive substring in description"),
    has_ai_suggestions: Optional[bool] = Query(None, description="Filter on stored AI category suggestions"),
    sort_by: str = Query("posted_at", description="posted_at|amount|description|category|business|income|adjustment"),
    sort_dir: str = Query("desc", description="asc|desc"),
    limit: int = 100,
    offset: int = 0,
):
    conn = get_conn()
    where = []
    params = []
    if uncategorized and category_id:
        raise HTTPException(status_code=400, detail="cannot combine uncategorized=true with category_id")
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
    if uncategorized:
        where.append("tc.category_id IS NULL")
    if is_business is not None:
        where.append("t.is_business = ?")
        params.append(is_business)
    if is_income is not None:
        where.append("t.is_income = ?")
        params.append(is_income)
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")
    if desc:
        where.append("lower(t.description_norm) LIKE ?")
        params.append(f"%{desc.lower()}%")
    if has_ai_suggestions is True:
        # Only show uncategorized transactions with AI suggestions (suggestions to review)
        where.append("t.ai_category_suggestions IS NOT NULL AND length(trim(t.ai_category_suggestions)) > 2 AND tc.category_id IS NULL")
    if has_ai_suggestions is False:
        where.append("(t.ai_category_suggestions IS NULL OR length(trim(t.ai_category_suggestions)) <= 2)")
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
    # Get total count first
    count_row = conn.execute(
        f"""
        SELECT COUNT(*) as cnt
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        """,
        params,
    ).fetchone()
    total = count_row[0] if count_row else 0

    rows = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               COALESCE(t.payee_alias, t.description_norm) AS payee,
               tc.category_id, c.name as category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer
               , t.is_business, t.is_income, t.is_adjustment, t.zelle_direction, t.zelle_counterparty
               , t.p2p_provider, t.p2p_direction, t.p2p_counterparty
               , t.ai_merchant_name, t.ai_category_suggestions, t.ai_confidence_score, t.ai_processed_at
               , t.reviewed_at, t.reviewed_by
        FROM [transaction] t
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
    # Return paginated response with total count
    return {
        "items": [TransactionItem(**i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1
    }


@router.get("/stats")
def transactions_stats(
    account_id: Optional[str] = None,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category_id: Optional[str] = Query(None),
    uncategorized: bool = Query(False),
    include_transfers: bool = Query(False),
    is_business: Optional[bool] = Query(None),
    is_income: Optional[bool] = Query(None),
    desc: Optional[str] = Query(None),
    has_ai_suggestions: Optional[bool] = Query(None),
):
    """Return total count and date bounds for transactions matching filters.

    Useful for UI to show "showing N of total" and pagination controls.
    """
    conn = get_conn()
    where = []
    params = []
    if uncategorized and category_id:
        raise HTTPException(status_code=400, detail="cannot combine uncategorized=true with category_id")
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
    if uncategorized:
        where.append("tc.category_id IS NULL")
    if is_business is not None:
        where.append("t.is_business = ?")
        params.append(is_business)
    if is_income is not None:
        where.append("t.is_income = ?")
        params.append(is_income)
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")
    if desc:
        where.append("lower(t.description_norm) LIKE ?")
        params.append(f"%{desc.lower()}%")
    if has_ai_suggestions is True:
        # Only show uncategorized transactions with AI suggestions (suggestions to review)
        where.append("t.ai_category_suggestions IS NOT NULL AND length(trim(t.ai_category_suggestions)) > 2 AND tc.category_id IS NULL")
    if has_ai_suggestions is False:
        where.append("(t.ai_category_suggestions IS NULL OR length(trim(t.ai_category_suggestions)) <= 2)")
    wh = " WHERE " + " AND ".join(where) if where else ""
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS total,
               MIN(t.posted_at) AS min_date,
               MAX(t.posted_at) AS max_date
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        """,
        params,
    ).fetchone()
    return {"total": int(row[0] or 0), "min_date": row[1], "max_date": row[2]}


@router.get("/accounts_summary")
def accounts_summary():
    """Return a small diagnostic summary for transaction imports."""
    conn = get_conn()
    row = conn.execute("SELECT COUNT(DISTINCT account_id) AS distinct_accounts FROM [transaction]").fetchone()
    return {"distinct_accounts": int((row[0] or 0) if row else 0)}


@router.get("/{tx_id}")
def get_transaction(tx_id: str):
    """Return a single transaction with joined fields consistent with list endpoint."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               COALESCE(t.payee_alias, t.description_norm) AS payee,
               tc.category_id, c.name as category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer
               , t.is_business, t.is_income, t.is_adjustment, t.zelle_direction, t.zelle_counterparty
               , t.p2p_provider, t.p2p_direction, t.p2p_counterparty
               , t.ai_merchant_name, t.ai_category_suggestions, t.ai_confidence_score, t.ai_processed_at
               , t.reviewed_at, t.reviewed_by
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        WHERE t.id = ?
        LIMIT 1
        """,
        [tx_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="transaction not found")
    cols = [c[0] for c in conn.description]
    item = dict(zip(cols, row))
    return TransactionItem(**item)


class PatchTxBody(BaseModel):
    is_business: Optional[bool] = None
    is_adjustment: Optional[bool] = None
    is_income: Optional[bool] = None
    p2p_provider: str | None = None
    p2p_direction: str | None = None
    p2p_counterparty: str | None = None
    ai_merchant_name: str | None = None


@router.patch("/{tx_id}")
def patch_transaction(tx_id: str, body: PatchTxBody):
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [tx_id]).fetchone()
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
    if body.p2p_provider is not None:
        provider = body.p2p_provider.strip() if isinstance(body.p2p_provider, str) else None
        sets.append("p2p_provider = ?")
        params.append(provider or None)
    if body.p2p_direction is not None:
        direction = body.p2p_direction.strip() if isinstance(body.p2p_direction, str) else None
        sets.append("p2p_direction = ?")
        params.append(direction or None)
    if body.p2p_counterparty is not None:
        counterparty = body.p2p_counterparty.strip() if isinstance(body.p2p_counterparty, str) else None
        sets.append("p2p_counterparty = ?")
        params.append(counterparty or None)
    if body.ai_merchant_name is not None:
        merchant = body.ai_merchant_name.strip() if isinstance(body.ai_merchant_name, str) else None
        sets.append("ai_merchant_name = ?")
        params.append(merchant or None)
    if not sets:
        return {"updated": 0}
    import json as _json
    from datetime import datetime as _dt, UTC as _UTC
    conn.execute(f"UPDATE [transaction] SET {', '.join(sets)} WHERE id = ?", params + [tx_id])
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transaction", tx_id, "patch", _json.dumps(body.dict(exclude_none=True)), _dt.now(_UTC), "user"],
    )
    return {"updated": 1}


@router.post("/{tx_id}/category")
async def assign_category(tx_id: str, body: AssignCategoryBody):
    conn = get_conn()
    # verify tx exists
    exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [tx_id]).fetchone()
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
    
    # MERCHANT MEMORY LEARNING - Learn from this categorization
    try:
        from ...ai_smart_categorization import learn_from_transaction_categorization
        await learn_from_transaction_categorization(tx_id, body.category_id)
    except Exception as e:
        # Don't fail the categorization if learning fails
        logger.warning(f"Failed to learn from categorization: {e}")
    
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
    exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [tx_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="transaction not found")
    # delete references
    conn.execute("DELETE FROM transaction_category WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction_tag WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM match_transfer WHERE left_tx_id = ? OR right_tx_id = ?", [tx_id, tx_id])
    conn.execute("DELETE FROM recurring_tx WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM transaction_ingest WHERE tx_id = ?", [tx_id])
    conn.execute("DELETE FROM [transaction] WHERE id = ?", [tx_id])
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
        FROM [transaction] WHERE id = ?
        """,
        [tx_id],
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="transaction not found")
    cols = [c[0] for c in conn.description]
    data = dict(zip(cols, row))
    return {"transaction": data}
class BatchBody(BaseModel):
    ids: list[str]


@router.post("/batch")
def get_transactions_batch(body: BatchBody):
    """Return multiple transactions by IDs in one call.

    Accepts {"ids": [..]} and returns a list of TransactionItem.
    """
    ids = list(dict.fromkeys((body.ids or [])))  # dedupe preserving order
    if not ids:
        return []
    conn = get_conn()
    qmarks = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               COALESCE(t.payee_alias, t.description_norm) AS payee,
               tc.category_id, c.name as category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer
               , t.is_business, t.is_income, t.is_adjustment, t.zelle_direction, t.zelle_counterparty
               , t.p2p_provider, t.p2p_direction, t.p2p_counterparty
               , t.ai_merchant_name, t.ai_category_suggestions, t.ai_confidence_score, t.ai_processed_at
               , t.reviewed_at, t.reviewed_by
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        WHERE t.id IN ({qmarks})
        """,
        ids,
    ).fetchall()
    cols = [c[0] for c in conn.description]
    items = [TransactionItem(**dict(zip(cols, r))) for r in rows]
    # Preserve requested order
    by_id = {i.id: i for i in items}
    return [by_id[i] for i in ids if i in by_id]


# =============================================================================
# Transaction Review Endpoints
# =============================================================================

class ReviewBody(BaseModel):
    """Mark transaction as reviewed."""
    reviewed_by: str = "user"


class BulkReviewBody(BaseModel):
    """Mark multiple transactions as reviewed."""
    tx_ids: list[str]
    reviewed_by: str = "user"


# Note: bulk routes must come BEFORE parameterized routes to avoid path matching issues
@router.post("/bulk/review")
def bulk_mark_reviewed(body: BulkReviewBody) -> dict:
    """Mark multiple transactions as reviewed."""
    conn = get_conn()

    if not body.tx_ids:
        return {"reviewed": 0, "tx_ids": []}

    # Dedupe and validate
    tx_ids = list(dict.fromkeys(body.tx_ids))
    qmarks = ",".join(["?"] * len(tx_ids))
    existing = conn.execute(
        f"SELECT id FROM [transaction] WHERE id IN ({qmarks})",
        tx_ids
    ).fetchall()
    existing_ids = {row[0] for row in existing}

    valid_ids = [tid for tid in tx_ids if tid in existing_ids]
    if not valid_ids:
        return {"reviewed": 0, "tx_ids": []}

    now = datetime.now(UTC).isoformat()
    qmarks = ",".join(["?"] * len(valid_ids))
    conn.execute(
        f"UPDATE [transaction] SET reviewed_at = ?, reviewed_by = ? WHERE id IN ({qmarks})",
        [now, body.reviewed_by] + valid_ids
    )

    # Log bulk review
    import json as _json
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transaction", "bulk", "bulk_review", _json.dumps({"tx_ids": valid_ids, "reviewed_by": body.reviewed_by}), now, body.reviewed_by],
    )

    return {"reviewed": len(valid_ids), "tx_ids": valid_ids}


@router.post("/{tx_id}/review")
def mark_reviewed(tx_id: str, body: ReviewBody) -> TransactionItem:
    """Mark a single transaction as reviewed."""
    conn = get_conn()

    exists = conn.execute("SELECT 1 FROM [transaction] WHERE id = ?", [tx_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="transaction not found")

    now = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE [transaction] SET reviewed_at = ?, reviewed_by = ? WHERE id = ?",
        [now, body.reviewed_by, tx_id]
    )

    # Log the review action
    import json as _json
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transaction", tx_id, "review", _json.dumps({"reviewed_by": body.reviewed_by}), now, body.reviewed_by],
    )

    return get_transaction(tx_id)


@router.get("/unreviewed/list")
def get_unreviewed(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_transfers: bool = Query(False)
) -> dict:
    """Get transactions that need review (reviewed_at is NULL)."""
    conn = get_conn()

    where = ["t.reviewed_at IS NULL"]
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")

    wh = " WHERE " + " AND ".join(where)

    # Get total count
    count_row = conn.execute(
        f"""
        SELECT COUNT(*) as cnt
        FROM [transaction] t
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        """
    ).fetchone()
    total = count_row[0] if count_row else 0

    rows = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               COALESCE(t.payee_alias, t.description_norm) AS payee,
               tc.category_id, c.name as category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer
               , t.is_business, t.is_income, t.is_adjustment, t.zelle_direction, t.zelle_counterparty
               , t.p2p_provider, t.p2p_direction, t.p2p_counterparty
               , t.ai_merchant_name, t.ai_category_suggestions, t.ai_confidence_score, t.ai_processed_at
               , t.reviewed_at, t.reviewed_by
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        ORDER BY t.posted_at DESC
        LIMIT ? OFFSET ?
        """,
        [limit, offset],
    ).fetchall()

    columns = [x[0] for x in conn.description]
    items = [dict(zip(columns, r)) for r in rows]

    return {
        "items": [TransactionItem(**i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1
    }
