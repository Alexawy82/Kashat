#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from apps.backend.src.kashat.parse.banks.boa_v2025 import parse_boa_pdf


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: reconcile_pdf_statement.py bank/eStmt_YYYY-MM-DD.pdf")
        sys.exit(1)
    pdf = sys.argv[1]
    data = Path(pdf).read_bytes()
    res = parse_boa_pdf(data)
    print("Period:", res.meta.get('period_start'), '→', res.meta.get('period_end'))
    print("Last4:", res.meta.get('account_last4'))
    # Extract header totals using text of page 1
    try:
        import pdfplumber
    except Exception:
        print("pdfplumber not installed; cannot read header totals")
        sys.exit(0)
    with pdfplumber.open(pdf) as f:
        text = (f.pages[0].extract_text() or "")
    dep_m = re.search(r"Deposits and other additions\s+\$?([\d,]+\.\d{2})", text)
    wdr_m = re.search(r"Withdrawals and other subtractions\s+\-?\$?([\d,]+\.\d{2})", text)
    if not dep_m or not wdr_m:
        print("Could not find header totals in statement")
        sys.exit(0)
    dep_total = float(dep_m.group(1).replace(",", ""))
    wdr_total = float(wdr_m.group(1).replace(",", ""))
    print("Header totals: deposits=", dep_total, "withdrawals=", wdr_total)
    # Compute from parsed rows
    inc = sum(r['amount'] for r in res.rows if r['amount'] > 0)
    deb = sum(-r['amount'] for r in res.rows if r['amount'] < 0)
    print("Parsed rows totals: income=", round(inc,2), "debits=", round(deb,2))
    if abs(inc - dep_total) < 0.01 and abs(deb - wdr_total) < 0.01:
        print("OK: parsed rows reconcile with header totals")
    else:
        print("MISMATCH: parsed vs header totals differ")


if __name__ == '__main__':
    main()

