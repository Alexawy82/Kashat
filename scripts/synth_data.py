#!/usr/bin/env python3
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


def main(n: int = 100000, accounts: int = 5):
    base = date(2024, 1, 1)
    out = Path('data/fixtures/synth.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    with out.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date','description','amount','currency'])
        for i in range(n):
            d = base + timedelta(days=rng.randint(0, 365))
            amt = round(rng.uniform(-200.0, 200.0), 2)
            desc = rng.choice(['STARBUCKS','RENT','PAYROLL','GROCERY','UBER','NETFLIX','TRANSFER FROM SAV 3454'])
            w.writerow([d.isoformat(), desc, f"{amt:.2f}", 'USD'])
    print('Wrote', out)


if __name__ == '__main__':
    main()

