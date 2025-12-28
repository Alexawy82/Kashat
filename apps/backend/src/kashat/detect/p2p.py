from __future__ import annotations

import re
from typing import Optional, Dict

from .zelle import parse_zelle_descriptor

_RE_GENERIC_VENMO = re.compile(r"\bvenmo\b", re.I)
_RE_GENERIC_CASHAPP = re.compile(r"\bcash\s*app\b", re.I)
_RE_GENERIC_WU = re.compile(r"\bwuvisaaft\b|\bwestern\s+union\b|\bwu\s*visa\s*aft\b", re.I)
_RE_GENERIC_PAYPAL = re.compile(r"\bpaypal\b|\bpp\*", re.I)
_RE_GENERIC_WIRE = re.compile(r"\bwire\s*(transfer|tfr)?\b|\bfed\s*wire\b|\bswift\b", re.I)

# Venmo patterns - multiple formats:
# "venmo *mai elm visa direct ny"
# "venmo *mai elm new york ny"
# "pmnt sent 1210 venmo *mai elm new york ny"
# The name ends before: visa direct, city+state (2-3 word location), or digits
_RE_VENMO_PATTERNS = [
    # venmo *name followed by "visa direct" or location
    re.compile(r"\bvenmo\s*\*\s*([a-z][a-z\s.'-]+?)(?:\s+visa\s+direct|\s+new\s+york|\s+[a-z]{2,12}\s+[a-z]{2}\b)", re.I),
    # venmo *name at end of string
    re.compile(r"\bvenmo\s*\*\s*([a-z][a-z\s.'-]+?)$", re.I),
    # venmo payment to/from name
    re.compile(r"\bvenmo\s+(?:payment\s+)?(?:to|from)\s+([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I),
]

# CashApp patterns
_RE_CASHAPP_PATTERNS = [
    re.compile(r"\bcash\s*app\s*\*\s*([a-z][a-z\s.'-]+?)(?:\s+[a-z]{2,}\s+[a-z]{2}\b|\s+\d{6,}|$)", re.I),
    re.compile(r"\bcashapp\s*\*\s*([a-z][a-z\s.'-]+?)(?:\s+[a-z]{2,}\s+[a-z]{2}\b|\s+\d{6,}|$)", re.I),
    re.compile(r"\bcash\s*app\s+(?:to|from)\s+([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I),
]

# PayPal patterns - multiple formats:
# PAYPAL *JOHNDOE 123456, PP*MERCHANT, PAYPAL INST XFER ID:MERCHANT INDN:NAME
# GAO MIN DES:IAT PAYPAL ID:xxx INDN:name  (international wire via PayPal)
# PURCHASE XXXX PAYPAL *MERCHANT city state
_RE_PAYPAL_PATTERNS = [
    # PayPal inst xfer with ID and INDN (name is after INDN:)
    re.compile(r"\bpaypal\s+(?:des:)?inst\s+xfer\s+id:([a-z][a-z0-9.\s-]+?)\s+indn:", re.I),
    # IAT PayPal - counterparty is the first name before DES:
    re.compile(r"^([a-z][a-z\s]+?)\s+des:iat\s+paypal\b", re.I),
    # PAYPAL *name followed by digits or city/state
    re.compile(r"\bpaypal\s*\*\s*([a-z][a-z\s.'-]+?)(?:\s+\d{6,}|\s+[a-z]{2,12}\s+[a-z]{2}\b|$)", re.I),
    # PP*name
    re.compile(r"\bpp\*\s*([a-z][a-z\s.'-]+?)(?:\s+\d{6,}|$)", re.I),
    # PAYPAL TRANSFER TO/FROM name
    re.compile(r"\bpaypal\s+(?:inst\s+)?(?:transfer|xfer)\s+(to|from)\s+([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I),
]

# Wire transfer patterns
# WIRE TRANSFER TO/FROM NAME, INCOMING WIRE FROM NAME, OUTGOING WIRE TO NAME
# FED WIRE TO NAME, WIRE TFR NAME
_RE_WIRE_DIRECTION = re.compile(r"\b(?:wire|fed\s*wire)\s*(?:transfer|tfr)?\s+(to|from)\s+([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I)
_RE_WIRE_INCOMING = re.compile(r"\b(?:incoming|inbound)\s+wire\s+(?:from\s+)?([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I)
_RE_WIRE_OUTGOING = re.compile(r"\b(?:outgoing|outbound)\s+wire\s+(?:to\s+)?([a-z][a-z\s.'-]+?)(?:\s+\d|$)", re.I)


def _clean_counterparty(name: str | None) -> str | None:
    if not name:
        return None
    s = name.strip()
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"[^a-z0-9\s.'-]+", "", s, flags=re.I).strip()
    return s or None


def parse_p2p_descriptor(desc_norm: str, amount: float | None = None) -> Optional[Dict[str, str]]:
    """Parse P2P provider/counterparty from a normalized transaction description.

    This is best-effort and intentionally conservative.
    """
    d = (desc_norm or "").strip()
    if not d:
        return None

    # Unify Zelle into P2P (we already have a dedicated Zelle parser)
    z = parse_zelle_descriptor(d)
    if z and z.get("type") == "zelle":
        out: Dict[str, str] = {
            "type": "p2p",
            "provider": "zelle",
            "direction": z.get("direction") or "unknown",
        }
        if z.get("counterparty"):
            out["counterparty"] = str(z["counterparty"]).strip()
        return out

    provider: str | None = None
    counterparty: str | None = None

    if _RE_GENERIC_VENMO.search(d):
        provider = "venmo"
        # Try multiple Venmo patterns
        for pattern in _RE_VENMO_PATTERNS:
            m = pattern.search(d)
            if m:
                counterparty = _clean_counterparty(m.group(1))
                break
    elif _RE_GENERIC_CASHAPP.search(d):
        provider = "cashapp"
        # Try multiple CashApp patterns
        for pattern in _RE_CASHAPP_PATTERNS:
            m = pattern.search(d)
            if m:
                counterparty = _clean_counterparty(m.group(1))
                break
    elif _RE_GENERIC_WU.search(d):
        provider = "western_union"
        counterparty = None
    elif _RE_GENERIC_PAYPAL.search(d):
        provider = "paypal"
        # Try multiple PayPal patterns
        for pattern in _RE_PAYPAL_PATTERNS:
            m = pattern.search(d)
            if m:
                # Check if this is a directional pattern (has 2 groups)
                if pattern.groups == 2 and m.lastindex == 2:
                    direction = "to" if m.group(1).lower() == "to" else "from"
                    counterparty = _clean_counterparty(m.group(2))
                    out: Dict[str, str] = {"type": "p2p", "provider": provider, "direction": direction}
                    if counterparty:
                        out["counterparty"] = counterparty
                    return out
                else:
                    counterparty = _clean_counterparty(m.group(1))
                    break
    elif _RE_GENERIC_WIRE.search(d):
        provider = "wire"
        # Try directional patterns
        m = _RE_WIRE_DIRECTION.search(d)
        if m:
            direction = "to" if m.group(1).lower() == "to" else "from"
            counterparty = _clean_counterparty(m.group(2))
            out: Dict[str, str] = {"type": "p2p", "provider": provider, "direction": direction}
            if counterparty:
                out["counterparty"] = counterparty
            return out
        # Incoming wire
        m = _RE_WIRE_INCOMING.search(d)
        if m:
            counterparty = _clean_counterparty(m.group(1))
            return {"type": "p2p", "provider": provider, "direction": "from", "counterparty": counterparty} if counterparty else {"type": "p2p", "provider": provider, "direction": "from"}
        # Outgoing wire
        m = _RE_WIRE_OUTGOING.search(d)
        if m:
            counterparty = _clean_counterparty(m.group(1))
            return {"type": "p2p", "provider": provider, "direction": "to", "counterparty": counterparty} if counterparty else {"type": "p2p", "provider": provider, "direction": "to"}
        counterparty = None
    else:
        return None

    direction = "unknown"
    if amount is not None:
        if amount < 0:
            direction = "to"
        elif amount > 0:
            direction = "from"

    out: Dict[str, str] = {"type": "p2p", "provider": provider, "direction": direction}
    if counterparty:
        out["counterparty"] = counterparty
    return out
