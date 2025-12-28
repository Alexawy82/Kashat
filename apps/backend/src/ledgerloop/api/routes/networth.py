"""
Net Worth API - Calculate and track net worth across accounts

Provides:
- Current net worth calculation (assets - liabilities)
- Breakdown by account type
- Historical net worth tracking
"""

import logging
from datetime import date, datetime, UTC, timedelta
from typing import Optional, List
import uuid

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ...db import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/networth", tags=["networth"])


# =============================================================================
# Models
# =============================================================================

class AccountBalance(BaseModel):
    """Account with balance for net worth calculation."""
    id: str
    name: str
    account_type: str
    balance: float


class NetWorthBreakdown(BaseModel):
    """Net worth breakdown by account type."""
    checking: float = 0.0
    savings: float = 0.0
    investment: float = 0.0
    asset: float = 0.0
    credit_card: float = 0.0
    loan: float = 0.0


class NetWorthResponse(BaseModel):
    """Current net worth response."""
    assets: float
    liabilities: float
    net_worth: float
    by_type: NetWorthBreakdown
    accounts: List[AccountBalance]
    as_of: str


class NetWorthPoint(BaseModel):
    """A point in net worth history."""
    date: str
    assets: float
    liabilities: float
    net_worth: float


# =============================================================================
# Helper Functions
# =============================================================================

def _calculate_account_balance(conn, account_id: str) -> float:
    """Calculate current balance for an account from transactions."""
    result = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) as balance
        FROM [transaction]
        WHERE account_id = ?
        """,
        [account_id]
    ).fetchone()
    return float(result[0]) if result else 0.0


def _get_account_type(account_type: Optional[str]) -> str:
    """Normalize account type with fallback."""
    valid_types = {'checking', 'savings', 'credit_card', 'loan', 'investment', 'asset'}
    if account_type and account_type.lower() in valid_types:
        return account_type.lower()
    return 'checking'


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
def get_net_worth() -> NetWorthResponse:
    """Calculate current net worth from all accounts."""
    conn = get_conn()

    # Get all accounts with their types (ledgerloop uses 'type' column)
    rows = conn.execute(
        """
        SELECT id, name, COALESCE(type, 'checking') as account_type
        FROM account
        ORDER BY name
        """
    ).fetchall()

    accounts = []
    breakdown = NetWorthBreakdown()
    total_assets = 0.0
    total_liabilities = 0.0

    for row in rows:
        account_id, name, account_type = row[0], row[1], row[2]
        account_type = _get_account_type(account_type)
        balance = _calculate_account_balance(conn, account_id)

        accounts.append(AccountBalance(
            id=account_id,
            name=name,
            account_type=account_type,
            balance=balance
        ))

        # Update breakdown
        if account_type == 'checking':
            breakdown.checking += balance
        elif account_type == 'savings':
            breakdown.savings += balance
        elif account_type == 'investment':
            breakdown.investment += balance
        elif account_type == 'asset':
            breakdown.asset += balance
        elif account_type == 'credit_card':
            breakdown.credit_card += balance
        elif account_type == 'loan':
            breakdown.loan += balance

        # Categorize as asset or liability
        if account_type in ('checking', 'savings', 'investment', 'asset'):
            total_assets += balance
        elif account_type in ('credit_card', 'loan'):
            # For liabilities, we take absolute value of negative balances
            total_liabilities += abs(balance) if balance < 0 else balance

    return NetWorthResponse(
        assets=round(total_assets, 2),
        liabilities=round(total_liabilities, 2),
        net_worth=round(total_assets - total_liabilities, 2),
        by_type=breakdown,
        accounts=accounts,
        as_of=datetime.now(UTC).isoformat()
    )


@router.get("/history")
def get_net_worth_history(
    months: int = Query(12, ge=1, le=60, description="Number of months to look back")
) -> List[NetWorthPoint]:
    """Get net worth over time (monthly snapshots).

    Calculates historical net worth by looking at transaction balances
    at the end of each month.
    """
    conn = get_conn()

    # Get all accounts (ledgerloop uses 'type' column)
    accounts = conn.execute(
        "SELECT id, COALESCE(type, 'checking') as account_type FROM account"
    ).fetchall()

    if not accounts:
        return []

    history = []
    today = date.today()

    for i in range(months):
        # Calculate end of month going back
        month_offset = months - 1 - i
        target_date = today.replace(day=1) - timedelta(days=1)  # Last day of previous month
        for _ in range(month_offset):
            target_date = target_date.replace(day=1) - timedelta(days=1)

        month_end = target_date.isoformat()

        total_assets = 0.0
        total_liabilities = 0.0

        for account_id, account_type in accounts:
            account_type = _get_account_type(account_type)

            # Calculate balance as of month end
            result = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as balance
                FROM [transaction]
                WHERE account_id = ? AND posted_at <= ?
                """,
                [account_id, month_end]
            ).fetchone()

            balance = float(result[0]) if result else 0.0

            if account_type in ('checking', 'savings', 'investment', 'asset'):
                total_assets += balance
            elif account_type in ('credit_card', 'loan'):
                total_liabilities += abs(balance) if balance < 0 else balance

        history.append(NetWorthPoint(
            date=month_end[:7],  # YYYY-MM format
            assets=round(total_assets, 2),
            liabilities=round(total_liabilities, 2),
            net_worth=round(total_assets - total_liabilities, 2)
        ))

    return history
