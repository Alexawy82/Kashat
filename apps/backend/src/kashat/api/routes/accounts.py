from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ...db import get_conn


router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    name: str
    type: Optional[str] = "checking"
    last4: Optional[str] = None
    currency: Optional[str] = "USD"
    institution_id: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    last4: Optional[str] = None
    currency: Optional[str] = None


@router.get("")
def list_accounts() -> List[Dict[str, Any]]:
    """List accounts with basic info and transaction counts."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT a.id, a.name, a.type, a.last4, a.currency, a.account_type,
               COUNT(t.id) AS transaction_count,
               MIN(t.posted_at) AS first_tx_date,
               MAX(t.posted_at) AS last_tx_date,
               COALESCE(SUM(t.amount), 0) AS balance
        FROM account a
        LEFT JOIN [transaction] t ON t.account_id = a.id
        GROUP BY a.id, a.name, a.type, a.last4, a.currency, a.account_type
        ORDER BY a.name
        """
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{account_id}")
def get_account(account_id: str) -> Dict[str, Any]:
    """Get a single account by ID with transaction stats."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT a.id, a.name, a.type, a.last4, a.currency, a.account_type,
               COUNT(t.id) AS transaction_count,
               MIN(t.posted_at) AS first_tx_date,
               MAX(t.posted_at) AS last_tx_date,
               COALESCE(SUM(t.amount), 0) AS balance
        FROM account a
        LEFT JOIN [transaction] t ON t.account_id = a.id
        WHERE a.id = ?
        GROUP BY a.id, a.name, a.type, a.last4, a.currency, a.account_type
        """,
        [account_id]
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    cols = [c[0] for c in conn.description]
    return dict(zip(cols, row))


@router.post("")
def create_account(body: AccountCreate) -> Dict[str, Any]:
    """Create a new account."""
    conn = get_conn()
    account_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO account (id, name, type, last4, currency, institution_id, account_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            account_id,
            body.name,
            body.type or "checking",
            body.last4,
            body.currency or "USD",
            body.institution_id,
            body.type or "checking"
        ]
    )

    return {
        "id": account_id,
        "name": body.name,
        "type": body.type or "checking",
        "last4": body.last4,
        "currency": body.currency or "USD",
        "transaction_count": 0,
        "balance": 0
    }


@router.put("/{account_id}")
def update_account(account_id: str, body: AccountUpdate) -> Dict[str, Any]:
    """Update an existing account."""
    conn = get_conn()

    # Check if account exists
    existing = conn.execute(
        "SELECT id FROM account WHERE id = ?",
        [account_id]
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    # Build update query dynamically
    updates = []
    params = []

    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name)
    if body.type is not None:
        updates.append("type = ?")
        params.append(body.type)
        updates.append("account_type = ?")
        params.append(body.type)
    if body.last4 is not None:
        updates.append("last4 = ?")
        params.append(body.last4)
    if body.currency is not None:
        updates.append("currency = ?")
        params.append(body.currency)

    if updates:
        params.append(account_id)
        conn.execute(
            f"UPDATE account SET {', '.join(updates)} WHERE id = ?",
            params
        )

    return get_account(account_id)


@router.delete("/{account_id}")
def delete_account(account_id: str, force: bool = False) -> Dict[str, str]:
    """Delete an account.

    By default, prevents deletion if account has transactions.
    Use force=true to delete anyway (transactions become orphaned).
    """
    conn = get_conn()

    # Check if account exists
    existing = conn.execute(
        "SELECT id, name FROM account WHERE id = ?",
        [account_id]
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check for transactions
    tx_count = conn.execute(
        "SELECT COUNT(*) FROM [transaction] WHERE account_id = ?",
        [account_id]
    ).fetchone()[0]

    if tx_count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Account has {tx_count} transactions. Use force=true to delete anyway."
        )

    # If force, unlink transactions first
    if tx_count > 0 and force:
        conn.execute(
            "UPDATE [transaction] SET account_id = NULL WHERE account_id = ?",
            [account_id]
        )

    # Delete the account
    conn.execute("DELETE FROM account WHERE id = ?", [account_id])

    return {"status": "deleted", "id": account_id, "name": existing[1]}
