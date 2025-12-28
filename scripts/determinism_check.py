#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import tempfile
import uuid
from pathlib import Path
import random
import hashlib


def has_duckdb() -> bool:
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


def main() -> None:
    if not has_duckdb():
        print("SKIP: duckdb not installed")
        return
    import importlib
    from datetime import datetime
    from kashat.db import close as db_close
    from kashat.db import get_conn
    from kashat.ingest_csv import import_csv_upload

    tmp = tempfile.mkdtemp(prefix="ll_det_")
    os.environ["KASHAT_DATA_DIR"] = tmp
    db_close()
    import kashat.db as dbmod
    importlib.reload(dbmod)

    fixtures = ["data/fixtures/sample_bank.csv", "data/fixtures/sample_bank2.csv", "data/fixtures/sample_bank3.csv"]
    def one_run(seed: str):
        order = fixtures[:]
        random.Random(seed).shuffle(order)
        for fn in order:
            with open(fn, "rb") as f:
                data = f.read()
            mid = random.randint(0, max(1, len(data)-1))
            for chunk in (data[:mid], data[mid:]):
                import_csv_upload(chunk if chunk else data, Path(fn).name, account_id="acc1")
            db_close(); importlib.reload(dbmod)
    seed = uuid.uuid4().hex
    one_run(seed)

    conn = get_conn()
    before = conn.execute("SELECT COUNT(*) FROM transaction").fetchone()[0]

    # Export normalized minimal subset to CSV
    export_path = Path(tmp) / "normalized_export.csv"
    rows = conn.execute(
        "SELECT posted_at, description_norm, amount, COALESCE(currency,'USD') FROM transaction ORDER BY posted_at, description_norm, amount"
    ).fetchall()
    with open(export_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "description", "amount", "currency"])
        w.writerows(rows)

    # Re-import exported CSV
    with open(export_path, "rb") as f:
        import_csv_upload(f.read(), "normalized_export.csv", account_id="acc1")

    after = conn.execute("SELECT COUNT(*) FROM transaction").fetchone()[0]
    if before != after:
        raise SystemExit(f"FAIL: counts differ before={before} after={after}")
    # Logical DB hash for run 1
    digest = hashlib.sha256()
    for r in conn.execute("SELECT id, account_id, posted_at, amount, description_norm FROM transaction ORDER BY id").fetchall():
        digest.update(str(r).encode())
    h1 = digest.hexdigest()
    print("Run 1 hash:", h1)

    # Two more randomized runs
    hashes = [h1]
    for i in range(2):
        tmp2 = tempfile.mkdtemp(prefix="ll_det_")
        os.environ["KASHAT_DATA_DIR"] = tmp2
        db_close(); importlib.reload(dbmod)
        seed = uuid.uuid4().hex
        one_run(seed)
        conn = get_conn()
        digest = hashlib.sha256()
        for r in conn.execute("SELECT id, account_id, posted_at, amount, description_norm FROM transaction ORDER BY id").fetchall():
            digest.update(str(r).encode())
        h = digest.hexdigest()
        print(f"Run {i+2} hash:", h)
        hashes.append(h)
    if len(set(hashes)) != 1:
        raise SystemExit("FAIL: determinism hash mismatch across runs")
    print("PASS: determinism check across 3 randomized runs")


if __name__ == "__main__":
    main()
