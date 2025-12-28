from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .. import PDFParseResult
from ...normalization import normalize_description, parse_date


HEADER_RE = re.compile(r"bank\s+of\s+america", re.I)
PERIOD_RE = re.compile(r"(?:statement\s+period[:\s]+|for\s+)([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})\s*(?:to|[-–])\s*([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})", re.I)
ACCT_RE = re.compile(r"account\s+(?:number|no\.)[:\s]+(?:[\d\s]{8,})(\d{4})|\*\*\*\*(\d{4})|Account\s+#\s*[\d\s]{8,}(\d{4})", re.I)
OPEN_BAL_RE = re.compile(r"beginning\s+balance.*?\$([\(\)\-\d\.,]+)", re.I)
CLOSE_BAL_RE = re.compile(r"ending\s+balance.*?\$([\(\)\-\d\.,]+)", re.I)

AMOUNT_RE = re.compile(r"^\$?([\(\)\-\+]?\d[\d,]*\.?\d{0,2})$")
DATE_LEAD_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4})\b")
LINE_RE = re.compile(r"^\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)\s+([()\-+]?\$?\d[\d,]*\.\d{2})\s*$")


def _to_amount(s: str) -> float:
    s = s.strip().replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        return -float(s.strip("()"))
    return float(s)


def _extract_header_text(pdf) -> str:
    text = "\n".join((page.extract_text() or "") for page in pdf.pages[:2])
    return text


def fingerprint(pdf) -> bool:
    try:
        text = _extract_header_text(pdf)
    except Exception:
        return False
    return bool(HEADER_RE.search(text))


def _parse_header(text: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    m = PERIOD_RE.search(text)
    if m:
        start_s, end_s = m.group(1), m.group(2)
        try:
            meta["period_start"] = parse_date(start_s)
            meta["period_end"] = parse_date(end_s)
        except Exception:
            pass
    m = ACCT_RE.search(text)
    if m:
        last4 = m.group(1) or m.group(2) or m.group(3)
        if last4:
            meta["account_last4"] = last4
    m = OPEN_BAL_RE.search(text)
    if m:
        try:
            meta["opening_balance"] = _to_amount(m.group(1))
        except Exception:
            pass
    m = CLOSE_BAL_RE.search(text)
    if m:
        try:
            meta["closing_balance"] = _to_amount(m.group(1))
        except Exception:
            pass
    return meta


def _parse_tables(pdf) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for page in pdf.pages:
        try:
            tables = page.extract_tables() or []
        except Exception:
            tables = []
        for tbl in tables:
            if not tbl or not tbl[0]:
                continue
            header = [h.strip().lower() if isinstance(h, str) else "" for h in tbl[0]]
            if not any("date" in h for h in header):
                continue
            # Identify candidate columns
            try:
                idx_date = next(i for i, h in enumerate(header) if "date" in h)
            except StopIteration:
                continue
            # Description column heuristic
            desc_candidates = [i for i, h in enumerate(header) if "description" in h or "transaction" in h]
            idx_desc = desc_candidates[0] if desc_candidates else (idx_date + 1)
            # Amount column heuristic
            amt_candidates = [i for i, h in enumerate(header) if "amount" in h and "balance" not in h]
            idx_amt = amt_candidates[0] if amt_candidates else None
            # Running balance column
            bal_candidates = [i for i, h in enumerate(header) if "balance" in h]
            idx_bal = bal_candidates[0] if bal_candidates else None

            for r in tbl[1:]:
                if idx_date >= len(r) or idx_desc >= len(r):
                    continue
                d = (r[idx_date] or "").strip()
                if not d or not DATE_LEAD_RE.match(d):
                    continue
                try:
                    posted_at = parse_date(d)
                except Exception:
                    continue
                desc = (r[idx_desc] or "").strip()
                amount = None
                if idx_amt is not None and idx_amt < len(r) and r[idx_amt]:
                    try:
                        amount = _to_amount(str(r[idx_amt]))
                    except Exception:
                        amount = None
                balance = None
                if idx_bal is not None and idx_bal < len(r) and r[idx_bal]:
                    try:
                        balance = _to_amount(str(r[idx_bal]))
                    except Exception:
                        balance = None
                if amount is None:
                    # If amount is missing but balance present, defer amount to text fallback
                    continue
                rows.append({
                    "posted_at": posted_at,
                    "description": desc,
                    "amount": amount,
                    "running_balance": balance,
                })
    return rows


def _parse_text(pdf) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            # Try original regex first
            m = LINE_RE.match(line)
            if m:
                d, desc, amt_s = m.groups()
                try:
                    posted_at = parse_date(d)
                    amt = _to_amount(amt_s.replace("$", ""))
                    rows.append({
                        "posted_at": posted_at,
                        "description": desc.strip(),
                        "amount": amt,
                        "running_balance": None,
                    })
                    continue
                except Exception:
                    pass
            
            # Try flexible parsing for BoA format
            if not DATE_LEAD_RE.match(line):
                continue
            
            # Extract date
            date_match = DATE_LEAD_RE.match(line)
            if not date_match:
                continue
            
            try:
                posted_at = parse_date(date_match.group(1))
            except Exception:
                continue
            
            # Find all potential amounts in the line (look for patterns like -49.98, 1,234.56, etc.)
            amount_pattern = re.compile(r'([()\-+]?\$?\d[\d,]*\.\d{2})')
            amounts = amount_pattern.findall(line)
            
            if not amounts:
                continue
            
            # Take the last amount as the transaction amount
            amt_s = amounts[-1]
            try:
                amt = _to_amount(amt_s.replace("$", ""))
            except Exception:
                continue
            
            # Extract description (everything between date and last amount)
            date_end = date_match.end()
            last_amount_pos = line.rfind(amt_s)
            if last_amount_pos > date_end:
                desc = line[date_end:last_amount_pos].strip()
            else:
                desc = line[date_end:].strip()
            
            if desc:  # Only add if we have a description
                rows.append({
                    "posted_at": posted_at,
                    "description": desc,
                    "amount": amt,
                    "running_balance": None,
                })
    return rows


def _validate_running_balance(rows: List[Dict[str, Any]], opening: Optional[float]) -> Tuple[List[str], Optional[float]]:
    anomalies: List[str] = []
    if opening is None:
        return anomalies, None
    # Sort by date stable
    rows_sorted = sorted(rows, key=lambda r: (r["posted_at"], r["description"]))
    bal = opening
    last_bal = None
    for i, r in enumerate(rows_sorted):
        bal += float(r["amount"]) if r.get("amount") is not None else 0.0
        last_bal = bal
        rb = r.get("running_balance")
        if rb is not None and abs(rb - bal) > 0.01:
            anomalies.append(f"running-balance mismatch at {i}: expected {bal:.2f} got {rb:.2f}")
    return anomalies, last_bal


def parse_boa_pdf(file_bytes: bytes) -> PDFParseResult:
    try:
        import pdfplumber  # type: ignore
    except Exception as e:
        raise ImportError("pdfplumber is required for BoA parser") from e
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        if not fingerprint(pdf):
            raise ValueError("Not a recognizable Bank of America statement")
        header_text = _extract_header_text(pdf)
        meta = _parse_header(header_text)
        rows = _parse_tables(pdf)
        if not rows:
            rows = _parse_text(pdf)

    # Normalize descriptions for consistency
    for r in rows:
        r["description_norm"] = normalize_description(r.get("description", ""))
        r["posted_at"] = r["posted_at"]

    anomalies, closing_by_calc = _validate_running_balance(rows, meta.get("opening_balance"))
    if closing_by_calc is not None:
        meta["closing_balance_calc"] = round(closing_by_calc, 2)
    return PDFParseResult(rows=rows, meta=meta, anomalies=anomalies)
