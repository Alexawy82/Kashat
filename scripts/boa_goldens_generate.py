#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
from pathlib import Path

import sys
from pathlib import Path as _P
sys.path.append(str(_P('apps/backend/src').resolve()))
from kashat.parse.banks.boa_v2025 import parse_boa_pdf


def main() -> None:
    pdfs = sorted(glob.glob('bank/*.pdf'))
    if not pdfs:
        print('No PDFs found in bank/*.pdf')
        return
    outdir = Path('data/fixtures')
    outdir.mkdir(parents=True, exist_ok=True)
    for pdf in pdfs:
        data = Path(pdf).read_bytes()
        try:
            res = parse_boa_pdf(data)
        except Exception as e:
            print('Skip (parse error):', pdf, e)
            continue
        base = Path(pdf).stem
        out = outdir / f'{base}.csv'
        with out.open('w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['date', 'description', 'amount'])
            for r in res.rows:
                w.writerow([r['posted_at'], r.get('description') or r.get('description_norm'), r['amount']])
        print('Wrote', out)


if __name__ == '__main__':
    main()
