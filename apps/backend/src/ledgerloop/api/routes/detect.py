from __future__ import annotations

from fastapi import APIRouter

from ...db import get_conn
from ...detect.zelle import parse_zelle_descriptor
from ...detect.income import mark_income
from ...detect.adjustments import mark_adjustments
from ...detect.p2p import parse_p2p_descriptor


router = APIRouter(prefix="/detect", tags=["detect"])


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
