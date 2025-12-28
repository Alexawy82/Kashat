#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path


LINE_RE = re.compile(r"^\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)\s+([()\-+]?\$?\d[\d,]*\.\d{2})\s*$")


def to_amount(s: str) -> float:
    s = s.strip().replace("$", "").replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        return -float(s.strip("()"))
    return float(s)


def gen_for_pdf(pdf_path: str):
    try:
        import pdfplumber  # type: ignore
    except Exception as e:
        raise SystemExit("pdfplumber required: pip install pdfplumber")
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = LINE_RE.match(line.strip())
                if not m:
                    continue
                d, desc, amt_s = m.groups()
                try:
                    amt = to_amount(amt_s)
                except Exception:
                    continue
                rows.append({"date": d, "description": desc.strip(), "amount": f"{amt:.2f}"})
    return rows


def main() -> None:
    outdir = Path('data/fixtures/boa_goldens')
    outdir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(glob.glob('bank/*.pdf'))
    if not pdfs:
        print('No PDFs in bank/*.pdf')
        return
    for pdf in pdfs:
        rows = gen_for_pdf(pdf)
        out = outdir / (Path(pdf).stem + '.csv')
        with out.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=["date", "description", "amount"])
            w.writeheader()
            w.writerows(rows)
        print('Golden written:', out)


if __name__ == '__main__':
    main()

