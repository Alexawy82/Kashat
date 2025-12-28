from __future__ import annotations

import re
from typing import Optional, Dict


_RE_FROM = re.compile(r"\bzelle\b.*\bfrom\b\s+([a-z][a-z\s.'-]+?)(?:\s+conf#|\s+\d|$)", re.I)
_RE_TO = re.compile(r"\bzelle\b.*\bto\b\s+([a-z][a-z\s.'-]+?)(?:\s+conf#|\s+\d|$)", re.I)
_RE_GENERIC = re.compile(r"\bzelle\b", re.I)

# Enhanced pattern to handle various Zelle formats
_RE_ZELLE_ENHANCED = re.compile(r"\bzelle\b\s+(from|to)\s+([a-z][a-z\s.'-]+?)(?:\s+(?:conf#|confirmation|\d))", re.I)


def parse_zelle_descriptor(desc: str) -> Optional[Dict[str, str]]:
    d = desc.strip()
    if not _RE_GENERIC.search(d):
        return None
    
    # Try enhanced pattern first
    m = _RE_ZELLE_ENHANCED.search(d)
    if m:
        direction = m.group(1).lower()
        name = m.group(2).strip()
        # Clean up the name by removing common artifacts
        name = re.sub(r'\s+conf#.*$', '', name, flags=re.I)
        name = re.sub(r'\s+confirmation.*$', '', name, flags=re.I)
        return {"type": "zelle", "direction": direction, "counterparty": name}
    
    # Fallback to original patterns
    m = _RE_FROM.search(d)
    if m:
        name = m.group(1).strip()
        # Clean up the name
        name = re.sub(r'\s+conf#.*$', '', name, flags=re.I)
        return {"type": "zelle", "direction": "from", "counterparty": name}
    
    m = _RE_TO.search(d)
    if m:
        name = m.group(1).strip()
        # Clean up the name
        name = re.sub(r'\s+conf#.*$', '', name, flags=re.I)
        return {"type": "zelle", "direction": "to", "counterparty": name}
    
    return {"type": "zelle", "direction": "unknown"}

