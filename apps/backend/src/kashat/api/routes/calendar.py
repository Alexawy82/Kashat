"""
Bill Calendar API - View upcoming recurring payments

Provides:
- Upcoming bills within a date range
- Monthly calendar view
- Bill frequency analysis
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List
from calendar import monthrange

from fastapi import APIRouter, Query, Path
from pydantic import BaseModel

from ...db import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


# =============================================================================
# Models
# =============================================================================

class UpcomingBill(BaseModel):
    """An upcoming recurring payment."""
    id: str
    name: str
    amount: float
    due_date: str
    recurring_type: Optional[str] = None
    cadence: Optional[str] = None
    is_essential: bool = False
    days_until: int = 0
    account_name: Optional[str] = None


class CalendarDay(BaseModel):
    """A day in the calendar with its bills."""
    date: str
    day: int
    bills: List[UpcomingBill]
    total_amount: float


class MonthCalendar(BaseModel):
    """Full month calendar view."""
    year: int
    month: int
    month_name: str
    days: List[CalendarDay]
    total_bills: int
    total_amount: float


class BillSummary(BaseModel):
    """Summary of upcoming bills."""
    next_7_days: float
    next_30_days: float
    next_90_days: float
    bill_count_7: int
    bill_count_30: int
    bill_count_90: int


# =============================================================================
# Helper Functions
# =============================================================================

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string, returning None if invalid."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None


def _get_upcoming_series(conn, start_date: date, end_date: date) -> List[dict]:
    """Get recurring series with next_date in the given range."""
    rows = conn.execute(
        """
        SELECT
            rs.id,
            COALESCE(rs.display_name, rs.name) as name,
            rs.amount_mean,
            rs.next_date,
            rs.recurring_type,
            rs.cadence,
            COALESCE(rs.is_essential, 0) as is_essential,
            a.name as account_name
        FROM recurring_series rs
        LEFT JOIN account a ON rs.account_id = a.id
        WHERE rs.status IN ('pending', 'confirmed')
          AND rs.next_date IS NOT NULL
          AND rs.next_date >= ?
          AND rs.next_date <= ?
        ORDER BY rs.next_date
        """,
        [start_date.isoformat(), end_date.isoformat()]
    ).fetchall()

    result = []
    today = date.today()

    for row in rows:
        next_date = _parse_date(row[3])
        days_until = (next_date - today).days if next_date else 0

        result.append({
            "id": row[0],
            "name": row[1] or "Unknown",
            "amount": abs(float(row[2] or 0)),
            "due_date": row[3],
            "recurring_type": row[4],
            "cadence": row[5],
            "is_essential": bool(row[6]),
            "days_until": days_until,
            "account_name": row[7]
        })

    return result


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/upcoming")
def get_upcoming_bills(
    days: int = Query(30, ge=1, le=365, description="Number of days to look ahead")
) -> List[UpcomingBill]:
    """Get upcoming recurring payments for the next N days."""
    conn = get_conn()

    today = date.today()
    end_date = today + timedelta(days=days)

    series = _get_upcoming_series(conn, today, end_date)

    return [UpcomingBill(**s) for s in series]


@router.get("/month/{year}/{month}")
def get_month_calendar(
    year: int = Path(..., ge=2000, le=2100),
    month: int = Path(..., ge=1, le=12)
) -> MonthCalendar:
    """Get all bills for a specific month as a calendar view."""
    conn = get_conn()

    # Get first and last day of month
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    series = _get_upcoming_series(conn, start_date, end_date)

    # Group by day
    days_dict = {}
    for day in range(1, last_day + 1):
        day_date = date(year, month, day)
        days_dict[day] = {
            "date": day_date.isoformat(),
            "day": day,
            "bills": [],
            "total_amount": 0.0
        }

    total_amount = 0.0
    for s in series:
        due = _parse_date(s["due_date"])
        if due and due.day in days_dict:
            days_dict[due.day]["bills"].append(UpcomingBill(**s))
            days_dict[due.day]["total_amount"] += s["amount"]
            total_amount += s["amount"]

    days = [
        CalendarDay(**days_dict[day])
        for day in range(1, last_day + 1)
    ]

    return MonthCalendar(
        year=year,
        month=month,
        month_name=MONTH_NAMES[month],
        days=days,
        total_bills=len(series),
        total_amount=round(total_amount, 2)
    )


@router.get("/summary")
def get_bill_summary() -> BillSummary:
    """Get summary of upcoming bills for different time periods."""
    conn = get_conn()

    today = date.today()

    # Get all upcoming bills for next 90 days
    series = _get_upcoming_series(conn, today, today + timedelta(days=90))

    # Calculate totals for each period
    total_7 = 0.0
    total_30 = 0.0
    total_90 = 0.0
    count_7 = 0
    count_30 = 0
    count_90 = 0

    for s in series:
        amount = s["amount"]
        days_until = s["days_until"]

        if days_until <= 7:
            total_7 += amount
            count_7 += 1
        if days_until <= 30:
            total_30 += amount
            count_30 += 1
        if days_until <= 90:
            total_90 += amount
            count_90 += 1

    return BillSummary(
        next_7_days=round(total_7, 2),
        next_30_days=round(total_30, 2),
        next_90_days=round(total_90, 2),
        bill_count_7=count_7,
        bill_count_30=count_30,
        bill_count_90=count_90
    )


@router.get("/today")
def get_todays_bills() -> List[UpcomingBill]:
    """Get bills due today."""
    conn = get_conn()

    today = date.today()
    series = _get_upcoming_series(conn, today, today)

    return [UpcomingBill(**s) for s in series]


@router.get("/overdue")
def get_overdue_bills() -> List[UpcomingBill]:
    """Get bills that are past due (next_date in the past)."""
    conn = get_conn()

    today = date.today()
    past_30 = today - timedelta(days=30)

    rows = conn.execute(
        """
        SELECT
            rs.id,
            COALESCE(rs.display_name, rs.name) as name,
            rs.amount_mean,
            rs.next_date,
            rs.recurring_type,
            rs.cadence,
            COALESCE(rs.is_essential, 0) as is_essential,
            a.name as account_name
        FROM recurring_series rs
        LEFT JOIN account a ON rs.account_id = a.id
        WHERE rs.status IN ('pending', 'confirmed')
          AND rs.next_date IS NOT NULL
          AND rs.next_date < ?
          AND rs.next_date >= ?
        ORDER BY rs.next_date
        """,
        [today.isoformat(), past_30.isoformat()]
    ).fetchall()

    result = []
    for row in rows:
        next_date = _parse_date(row[3])
        days_until = (next_date - today).days if next_date else 0

        result.append(UpcomingBill(
            id=row[0],
            name=row[1] or "Unknown",
            amount=abs(float(row[2] or 0)),
            due_date=row[3],
            recurring_type=row[4],
            cadence=row[5],
            is_essential=bool(row[6]),
            days_until=days_until,
            account_name=row[7]
        ))

    return result
