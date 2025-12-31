from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Tuple

# Avoid importing DB at module import to keep pure helpers testable without sqlite3


def _canonical_pair(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a < b else (b, a)


def jaccard_similarity(a: str, b: str) -> float:
    """Very simple token-level similarity for descriptions."""
    ta = {t for t in a.split() if t}
    tb = {t for t in b.split() if t}
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _score_pair(day_diff: int, max_days: int, desc_sim: float) -> float:
    day_score = max(0.0, 1.0 - (abs(day_diff) / max_days)) if max_days > 0 else 1.0
    return 0.5 * day_score + 0.5 * desc_sim


def suggest_transfers(max_days: int = 3, amount_tolerance: float = 0.01, limit: int = 1000) -> Dict[str, int]:
    """Scan for potential transfer pairs and insert suggestions.

    Criteria:
    - Opposite signs and near-zero sum within tolerance
    - Posted within +/- max_days
    - Different accounts
    - Not already suggested/confirmed
    """
    from .db import get_conn
    conn = get_conn()
    rows = conn.execute(
        f"""
        SELECT t1.id AS a_id, t2.id AS b_id,
               t1.posted_at AS a_date, t2.posted_at AS b_date,
               t1.amount AS a_amount, t2.amount AS b_amount,
               t1.description_norm AS a_desc, t2.description_norm AS b_desc,
               CAST(julianday(t2.posted_at) - julianday(t1.posted_at) AS INTEGER) AS day_diff
        FROM "transaction" t1
        JOIN "transaction" t2 ON t1.id < t2.id
        WHERE t1.account_id <> t2.account_id
          AND t1.amount * t2.amount < 0
          AND abs(t1.amount + t2.amount) <= ?
          AND abs(julianday(t2.posted_at) - julianday(t1.posted_at)) <= ?
          AND t1.is_income = FALSE
          AND t2.is_income = FALSE
        LIMIT ?
        """,
        [amount_tolerance, max_days, limit],
    ).fetchall()

    suggested = 0
    skipped_existing = 0
    for a_id, b_id, a_date, b_date, a_amt, b_amt, a_desc, b_desc, day_diff in rows:
        if _is_income_description(a_desc) or _is_income_description(b_desc):
            continue
        left, right = _canonical_pair(a_id, b_id)
        exists = conn.execute(
            "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
            [left, right],
        ).fetchone()
        if exists:
            skipped_existing += 1
            continue
        sim = jaccard_similarity(a_desc or "", b_desc or "")
        score = _score_pair(int(day_diff), max_days, sim)
        if score < 0.5:
            continue
        conn.execute(
            "INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at, group_id) VALUES (?, ?, ?, ?, ?, ?)",
            [left, right, float(score), "heuristic-v1", None, None],
        )
        suggested += 1
    return {"suggested": suggested, "skipped_existing": skipped_existing}


# v2 descriptor-based pairing
import re
# Primary BoA phrasing
_RE_OB = re.compile(r"online\s+banking\s+transfer\s+(from|to)\s+(sav|chk)\s+(\d{4})", re.I)
# Additional variants often seen in statements after normalization
_RE_OB_ALT = [
    re.compile(r"\bob\s+transfer\s+(from|to)\s+(sav|chk)\s+(\d{4})", re.I),
    re.compile(r"\bonline\s+transfer\s+(from|to)\s+(sav|chk)\s+(\d{4})", re.I),
    re.compile(r"transfer\s+(?:to|from)\s+(savings|checking).*?(\d{4})", re.I),
]

_INCOME_DESC_RE = re.compile(
    r"\b(payroll|paycheck|salary|direct\s+deposit|employer|adp|gusto|paychex|paylocity|paycom|intuit)\b",
    re.I,
)


def _parse_ob(desc: str):
    d = desc or ""
    m = _RE_OB.search(d)
    if m:
        return {"direction": m.group(1).lower(), "acct_type": m.group(2).lower(), "last4": m.group(3)}
    # Try alternates
    for rx in _RE_OB_ALT:
        m2 = rx.search(d)
        if m2:
            # Map account type if needed
            acct = (m2.group(2) if rx is not _RE_OB_ALT[2] else ("sav" if m2.group(1).lower().startswith('sav') else "chk"))
            if rx is _RE_OB_ALT[2]:
                direction = 'to' if 'to' in d.lower() else ('from' if 'from' in d.lower() else None)
            else:
                direction = m2.group(1).lower()
            return {"direction": direction, "acct_type": acct.lower(), "last4": m2.group(2 if rx is not _RE_OB_ALT[2] else 2)}
    return None


def _is_income_description(desc: str | None) -> bool:
    if not desc:
        return False
    return bool(_INCOME_DESC_RE.search(desc))


def _parse_date(dt) -> datetime:
    """Parse date from string or return as-is if already datetime."""
    if isinstance(dt, datetime):
        return dt
    if isinstance(dt, str):
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    return datetime.now(UTC)


def suggest_transfers_v2(max_days: int = 2, amount_tolerance: float = 0.01, limit: int = 5000) -> Dict[str, int]:
    from .db import get_conn

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, account_id, posted_at, amount, description_norm
        FROM [transaction]
        WHERE LOWER(description_norm) LIKE '%transfer%'
          AND is_income = FALSE
        ORDER BY posted_at
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    parsed = []
    for id_, acc, dt, amt, desc in rows:
        if _is_income_description(desc):
            continue
        info = _parse_ob(desc or "")
        if info:
            parsed.append({"id": id_, "account_id": acc, "posted_at": _parse_date(dt), "amount": amt, "info": info})

    suggested = 0
    for i, a in enumerate(parsed):
        for j in range(i + 1, len(parsed)):
            b = parsed[j]
            if abs((b["posted_at"] - a["posted_at"]).days) > max_days:
                continue
            # pair requires opposite sign, near equal amount, same last4 target
            if a["amount"] * b["amount"] >= 0:
                continue
            if abs(abs(a["amount"]) - abs(b["amount"])) > amount_tolerance:
                continue
            # One must be 'from' and the other 'to' and share last4
            ai, bi = a["info"], b["info"]
            if ai["last4"] != bi["last4"]:
                continue
            dirs = {ai["direction"], bi["direction"]}
            if not ("from" in dirs and "to" in dirs):
                continue
            left, right = _canonical_pair(a["id"], b["id"])
            exists = conn.execute(
                "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
                [left, right],
            ).fetchone()
            if exists:
                continue
            gid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at, group_id) VALUES (?, ?, ?, ?, ?, ?)",
                [left, right, 1.0, "descriptor-v2", None, gid],
            )
            suggested += 1
    return {"suggested": suggested}


def list_transfers(status: str = "pending") -> List[Dict]:
    from .db import get_conn
    conn = get_conn()
    where = {
        "pending": "mt.decided_at IS NULL",
        "confirmed": "mt.decided_at IS NOT NULL",
        "all": "1=1",
    }.get(status, "mt.decided_at IS NULL")
    rows = conn.execute(
        f"""
        SELECT mt.left_tx_id, mt.right_tx_id, mt.score, mt.method, mt.decided_at, mt.group_id, mt.include_in_analytics,
               ta.posted_at AS left_date, ta.amount AS left_amount, ta.description_norm AS left_desc, ta.account_id AS left_account_id,
               tb.posted_at AS right_date, tb.amount AS right_amount, tb.description_norm AS right_desc, tb.account_id AS right_account_id
        FROM match_transfer mt
        JOIN [transaction] ta ON ta.id = mt.left_tx_id
        JOIN [transaction] tb ON tb.id = mt.right_tx_id
        WHERE {where}
        ORDER BY COALESCE(mt.decided_at, '1970-01-01') DESC, mt.score DESC
        """
    ).fetchall()
    cols = [c[0] for c in conn.description]
    return [dict(zip(cols, r)) for r in rows]


def confirm_transfer(a: str, b: str) -> Dict[str, str]:
    from .db import get_conn
    conn = get_conn()
    left, right = _canonical_pair(a, b)
    now = datetime.now(UTC)
    row = conn.execute(
        "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
        [left, right],
    ).fetchone()
    if not row:
        # create it if it was not suggested
        gid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at, group_id) VALUES (?, ?, ?, ?, ?, ?)",
            [left, right, 1.0, "manual", now, gid],
        )
    else:
        gid = str(uuid.uuid4())
        conn.execute(
            "UPDATE match_transfer SET decided_at = ?, group_id = ? WHERE left_tx_id = ? AND right_tx_id = ?",
            [now, gid, left, right],
        )
    # audit log
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transfer", left, "confirm", json.dumps({"right": right}), now, "user"],
    )
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transfer", right, "confirm", json.dumps({"left": left}), now, "user"],
    )
    return {"left_tx_id": left, "right_tx_id": right, "group_id": gid}


def reject_transfer(a: str, b: str) -> Dict[str, str]:
    from .db import get_conn
    conn = get_conn()
    left, right = _canonical_pair(a, b)
    conn.execute(
        "DELETE FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ? AND decided_at IS NULL",
        [left, right],
    )
    conn.execute(
        "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), "transfer", left, "reject", json.dumps({"right": right}), datetime.now(UTC), "user"],
    )
    return {"left_tx_id": left, "right_tx_id": right}


# Transfer-related category patterns (case-insensitive matching)
_TRANSFER_CATEGORY_PATTERNS = [
    "internal transfer",
    "transfer",
    "transfers",
    "zelle",
    "venmo",
    "paypal transfer",
    "wire transfer",
    "ach transfer",
]


def _is_transfer_category(cat_name: str | None) -> bool:
    """Check if category name indicates a transfer."""
    if not cat_name:
        return False
    lower = cat_name.lower().strip()
    return any(pattern in lower for pattern in _TRANSFER_CATEGORY_PATTERNS)


def _transfer_description_keywords(desc: str | None) -> bool:
    """Check if description contains transfer-related keywords."""
    if not desc:
        return False
    lower = desc.lower()
    keywords = ["transfer", "zelle", "venmo", "wire", "ach", "xfer", "tfr"]
    return any(kw in lower for kw in keywords)


def suggest_transfers_v3(
    max_days: int = 3,
    amount_tolerance_pct: float = 0.02,
    min_score: float = 0.5,
    limit: int = 5000,
) -> Dict[str, int]:
    """Hybrid transfer detection combining category awareness and amount matching.

    This version improves on v2 by:
    1. Including transactions categorized as transfers (Internal Transfer, Zelle, etc.)
    2. Using fuzzy amount matching with percentage tolerance
    3. Scoring based on category match, description similarity, and date proximity

    Args:
        max_days: Maximum days apart for a potential pair
        amount_tolerance_pct: Percentage tolerance for amount matching (0.02 = 2%)
        min_score: Minimum score to suggest a pair
        limit: Maximum transactions to scan

    Returns:
        Dict with suggested count and stats
    """
    from .db import get_conn

    conn = get_conn()

    # Get all transactions with transfer-related categories OR transfer keywords in description
    # Join with transaction_category and category to get category names
    rows = conn.execute(
        """
        SELECT DISTINCT
            t.id,
            t.account_id,
            t.posted_at,
            t.amount,
            t.description_norm,
            t.is_income,
            COALESCE(c.name, '') AS category_name
        FROM [transaction] t
        LEFT JOIN transaction_category tc ON tc.tx_id = t.id
        LEFT JOIN category c ON tc.category_id = c.id
        WHERE (
            -- Has transfer-related category
            LOWER(c.name) LIKE '%transfer%'
            OR LOWER(c.name) LIKE '%zelle%'
            OR LOWER(c.name) LIKE '%venmo%'
            -- OR has transfer-related description
            OR LOWER(t.description_norm) LIKE '%transfer%'
            OR LOWER(t.description_norm) LIKE '%zelle%'
            OR LOWER(t.description_norm) LIKE '%venmo%'
            OR LOWER(t.description_norm) LIKE '%xfer%'
        )
          AND t.is_income = FALSE
        ORDER BY t.posted_at DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()

    # Build candidate list with metadata
    candidates = []
    for id_, acc, posted_at, amount, desc, is_income, cat_name in rows:
        if is_income or _is_income_description(desc):
            continue
        has_transfer_cat = _is_transfer_category(cat_name)
        has_transfer_desc = _transfer_description_keywords(desc)
        candidates.append({
            "id": id_,
            "account_id": acc,
            "posted_at": _parse_date(posted_at),
            "amount": float(amount),
            "description": desc or "",
            "category": cat_name or "",
            "has_transfer_cat": has_transfer_cat,
            "has_transfer_desc": has_transfer_desc,
        })

    # Find matching pairs
    suggested = 0
    skipped_existing = 0
    skipped_low_score = 0

    for i, a in enumerate(candidates):
        for j in range(i + 1, len(candidates)):
            b = candidates[j]

            # Must be different accounts
            if a["account_id"] == b["account_id"]:
                continue

            # Must have opposite signs
            if a["amount"] * b["amount"] >= 0:
                continue

            # Check date proximity
            day_diff = abs((b["posted_at"] - a["posted_at"]).days)
            if day_diff > max_days:
                continue

            # Check amount match (with percentage tolerance)
            abs_a = abs(a["amount"])
            abs_b = abs(b["amount"])
            avg_amt = (abs_a + abs_b) / 2.0
            amount_diff = abs(abs_a - abs_b)
            tolerance = max(0.01, avg_amt * amount_tolerance_pct)  # At least 1 cent

            if amount_diff > tolerance:
                continue

            # Calculate score
            # 1. Date proximity score (0-1, closer = higher)
            date_score = 1.0 - (day_diff / max(max_days, 1))

            # 2. Amount match score (0-1, closer = higher)
            amount_score = 1.0 - (amount_diff / max(tolerance, 0.01))

            # 3. Category match score
            cat_score = 0.0
            if a["has_transfer_cat"] and b["has_transfer_cat"]:
                cat_score = 1.0
            elif a["has_transfer_cat"] or b["has_transfer_cat"]:
                cat_score = 0.6

            # 4. Description similarity score
            desc_sim = jaccard_similarity(a["description"], b["description"])

            # 5. Description keyword bonus
            keyword_bonus = 0.0
            if a["has_transfer_desc"] and b["has_transfer_desc"]:
                keyword_bonus = 0.2
            elif a["has_transfer_desc"] or b["has_transfer_desc"]:
                keyword_bonus = 0.1

            # Combined score with weights
            score = (
                0.20 * date_score +
                0.25 * amount_score +
                0.25 * cat_score +
                0.15 * desc_sim +
                0.15 * keyword_bonus
            )

            # Boost if both have strong transfer signals
            if a["has_transfer_cat"] and b["has_transfer_cat"]:
                score = min(1.0, score + 0.15)

            if score < min_score:
                skipped_low_score += 1
                continue

            # Check if pair already exists
            left, right = _canonical_pair(a["id"], b["id"])
            exists = conn.execute(
                "SELECT 1 FROM match_transfer WHERE left_tx_id = ? AND right_tx_id = ?",
                [left, right],
            ).fetchone()
            if exists:
                skipped_existing += 1
                continue

            # Insert suggestion
            gid = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at, group_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [left, right, float(score), "hybrid-v3", None, gid],
            )
            suggested += 1

    return {
        "suggested": suggested,
        "skipped_existing": skipped_existing,
        "skipped_low_score": skipped_low_score,
        "candidates_scanned": len(candidates),
    }
