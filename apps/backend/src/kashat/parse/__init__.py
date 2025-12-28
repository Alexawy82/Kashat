from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PDFParseResult:
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any]
    anomalies: List[str]

