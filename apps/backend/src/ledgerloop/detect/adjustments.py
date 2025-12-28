from __future__ import annotations

import re
from typing import Iterable, List, Dict


ADJ_RE = re.compile(r"\b(cashback|fee\s+reversal|reversal|adjustment|courtesy\s+credit)\b", re.I)


def mark_adjustments(records: Iterable[Dict]) -> List[str]:
    """Return list of tx_ids flagged as adjustments (credits to exclude from spend)."""
    ids: List[str] = []
    for t in records:
        amount = float(t.get("amount", 0.0))
        if amount <= 0:
            continue
        desc = t.get("description_norm", "")
        if ADJ_RE.search(desc):
            ids.append(t["id"])
    return ids

