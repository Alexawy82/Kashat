from __future__ import annotations

import re
from datetime import datetime, date
from typing import Optional


_WS_RE = re.compile(r"\s+")
_PUNCT_TRIM_RE = re.compile(r"^[\s\-:\|\.,_]+|[\s\-:\|\.,_]+$")


def normalize_description(s: str) -> str:
    s2 = s.strip().lower()
    s2 = _WS_RE.sub(" ", s2)
    s2 = _PUNCT_TRIM_RE.sub("", s2)
    return s2


def parse_amount(amount: Optional[str], credit: Optional[str], debit: Optional[str]) -> float:
    def to_float(x: Optional[str]) -> Optional[float]:
        if x is None:
            return None
        s = x.replace(",", "").strip()
        if not s:
            return None
        return float(s)

    if amount is not None and amount != "":
        return to_float(amount) or 0.0
    c = to_float(credit)
    d = to_float(debit)
    if c is not None and d is not None:
        return c - d
    if c is not None:
        return c
    if d is not None:
        return -d
    return 0.0


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m/%d/%y",
    "%d/%m/%y",
    "%B %d, %Y",
    "%b %d, %Y",
]


def parse_date(s: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except Exception:
            continue
    # Last resort: try ISO-like coercion
    return datetime.fromisoformat(s.strip()).date()


def currency_or_default(s: Optional[str]) -> str:
    if s and s.strip():
        return s.strip().upper()
    return "USD"
