from __future__ import annotations

import csv
from io import StringIO
from typing import Optional
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from ...db import get_conn
from datetime import datetime, UTC
import json


router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions.csv")
def export_transactions(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    account_id: Optional[str] = Query(None),
):
    conn = get_conn()
    where = []
    params = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if account_id:
        where.append("t.account_id = ?")
        params.append(account_id)
    wh = " WHERE " + " AND ".join(where) if where else ""
    cursor = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               tc.category_id, c.name AS category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer,
               rtx.series_id AS recurring_series_id, t.zelle_direction, t.zelle_counterparty
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        LEFT JOIN recurring_tx rtx ON rtx.tx_id = t.id
        {wh}
        ORDER BY t.posted_at
        """,
        params,
    )
    cols = [c[0] for c in conn.description]
    def _iter():
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(cols)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for r in cursor:
            writer.writerow(r)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=transactions.csv"})


@router.get("/csv")
def export_csv(
    start_date: Optional[date] = Query(None, alias="from"),
    end_date: Optional[date] = Query(None, alias="to"),
    only_business: bool = Query(False, alias="onlyBusiness"),
    include_transfers: bool = Query(False, alias="includeTransfers"),
):
    """Streaming CSV export that mirrors Transactions table filters.

    Logs an event to event_log with action 'export:csv'.
    """
    conn = get_conn()
    where = []
    params = []
    if start_date:
        where.append("t.posted_at >= ?")
        params.append(start_date)
    if end_date:
        where.append("t.posted_at <= ?")
        params.append(end_date)
    if only_business:
        where.append("(t.is_business IS TRUE)")
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")

    wh = (" WHERE " + " AND ".join(where)) if where else ""

    count_row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        LEFT JOIN recurring_tx rtx ON rtx.tx_id = t.id
        {wh}
        """,
        params,
    ).fetchone()
    total_rows = int(count_row[0] or 0) if count_row else 0

    cursor = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               tc.category_id, c.name AS category_name,
               CASE WHEN mt.left_tx_id IS NOT NULL OR mt.right_tx_id IS NOT NULL THEN true ELSE false END AS is_transfer,
               t.is_business, t.is_income, t.is_adjustment,
               rtx.series_id AS recurring_series_id, t.zelle_direction, t.zelle_counterparty
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        LEFT JOIN recurring_tx rtx ON rtx.tx_id = t.id
        {wh}
        ORDER BY t.posted_at
        """,
        params,
    )
    cols = [c[0] for c in conn.description]

    # Log to event_log (redact free-text)
    try:
        payload = {
            "from": str(start_date) if start_date else None,
            "to": str(end_date) if end_date else None,
            "onlyBusiness": only_business,
            "includeTransfers": include_transfers,
            "rowCount": total_rows,
        }
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                f"evt_{int(datetime.now(UTC).timestamp()*1000)}",
                "export",
                "csv",
                "export:csv",
                json.dumps(payload),
                datetime.now(UTC),
                "system",
            ],
        )
    except Exception:
        pass

    # Streaming response
    def _iter():
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(cols)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)
        for r in cursor:
            writer.writerow(r)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

    # File name with date range
    def _fname() -> str:
        f = start_date.isoformat() if start_date else "all"
        t = end_date.isoformat() if end_date else "all"
        return f"transactions_{f}_{t}.csv"

    return StreamingResponse(_iter(), media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={_fname()}"
    })


@router.post("")
def export_presets(
    format: str = Query("csv", pattern="^(csv|parquet)$"),
    business_only: bool = Query(False),
    include_transfers: bool = Query(False),
    include_adjustments: bool = Query(False),
):
    conn = get_conn()
    where = []
    params = []
    if not include_transfers:
        where.append("(mt.left_tx_id IS NULL AND mt.right_tx_id IS NULL)")
    if not include_adjustments:
        where.append("(t.is_adjustment IS FALSE OR t.is_adjustment IS NULL)")
    if business_only:
        where.append("(t.is_business IS TRUE)")
    wh = (" WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"""
        SELECT t.id, t.account_id, t.posted_at, t.amount, t.currency, t.description_norm,
               tc.category_id, c.name AS category_name
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON t.id = tc.tx_id
        LEFT JOIN category c ON tc.category_id = c.id
        LEFT JOIN match_transfer mt ON (t.id = mt.left_tx_id OR t.id = mt.right_tx_id) AND mt.decided_at IS NOT NULL
        {wh}
        ORDER BY t.posted_at
        """,
        params,
    ).fetchall()
    cols = [c[0] for c in conn.description]

    if format == "csv":
        def _iter():
            buf = StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)
            for r in rows:
                writer.writerow(r)
                yield buf.getvalue()
                buf.seek(0); buf.truncate(0)
        return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})

    # parquet
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except Exception as e:
        return {"error": "pyarrow not installed", "count": len(rows)}
    table = pa.Table.from_arrays([pa.array([r[i] for r in rows]) for i in range(len(cols))], names=cols)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    buf = sink.getvalue().to_pybytes()
    return StreamingResponse(iter([buf]), media_type="application/octet-stream", headers={"Content-Disposition": "attachment; filename=export.parquet"})
