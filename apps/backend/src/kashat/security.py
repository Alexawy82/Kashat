from __future__ import annotations

import re


_RE_ACCT = re.compile(r"(account\s*(?:number|#)\s*:?\s*)([\d\s]{8,})(\d{4})", re.I)
_RE_DIGITS = re.compile(r"\b(\d{12,})\b")


def redact(text: str) -> str:
    s = _RE_ACCT.sub(lambda m: m.group(1) + "****" + m.group(3), text)
    s = _RE_DIGITS.sub(lambda m: "***REDACTED***", s)
    return s

