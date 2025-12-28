from __future__ import annotations

import hashlib
from datetime import date


def tx_fingerprint(account_id: str, posted_at: date, amount: float, description_norm: str) -> str:
    base = f"{account_id}|{posted_at.isoformat()}|{abs(amount):.2f}|{description_norm}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()
