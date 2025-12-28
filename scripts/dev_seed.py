"""
Deterministic dev seed script.

Creates:
- Two accounts (checking, savings)
- ~300 transactions across 6 months
- Clear recurring series (NETFLIX monthly, RENT monthly)
- Transfer pairs between checking and savings
- Two import runs with files and summaries

Usage: KASHAT_ENV=dev python -m scripts.dev_seed
Never include in production images.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta
from random import Random

from apps.backend.src.kashat.db import get_conn


def _ensure_accounts(conn):
    accounts = [
        ("acc_chk", "Checking", "chk", "USD"),
        ("acc_sav", "Savings", "sav", "USD"),
    ]
    for aid, name, type_, cur in accounts:
        conn.execute(
            "INSERT OR IGNORE INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)",
            [aid, name, type_, cur],
        )
    return [a[0] for a in accounts]


def _mk_tx(conn, account_id: str, d: date, amount: float, desc: str) -> str:
    tid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO transaction (id, account_id, posted_at, amount, currency, description_norm, fingerprint, created_at)
        VALUES (?, ?, ?, ?, 'USD', ?, ?, ?)
        """,
        [tid, account_id, d, amount, desc.lower(), f"{account_id}|{d}|{amount:.2f}|{desc.lower()}", datetime.utcnow()],
    )
    return tid


def seed_transactions(conn):
    rng = Random(42)
    acc_chk, acc_sav = _ensure_accounts(conn)
    # Time window: last 6 months
    today = date.today()
    start = today - timedelta(days=180)
    tx_count = 0
    # Random everyday spend/income
    for i in range(260):
        d = start + timedelta(days=rng.randrange(0, 180))
        if rng.random() < 0.6:
            amt = -round(rng.uniform(5.0, 120.0), 2)
            desc = rng.choice(["COFFEE SHOP", "GROCERY", "UBER", "AMAZON"])
            _mk_tx(conn, acc_chk, d, amt, desc)
        else:
            amt = round(rng.uniform(50.0, 500.0), 2)
            desc = rng.choice(["CASHBACK", "REFUND", "PAYROLL PARTIAL"])
            _mk_tx(conn, acc_chk, d, amt, desc)
        tx_count += 1

    # Recurring: NETFLIX monthly on the 5th, -15.99
    for m in range(6):
        d = (start.replace(day=5) + timedelta(days=30 * m))
        _mk_tx(conn, acc_chk, d, -15.99, "NETFLIX")
        tx_count += 1
    # Recurring: RENT monthly on 1st, -900.00
    for m in range(6):
        d = (start.replace(day=1) + timedelta(days=30 * m))
        _mk_tx(conn, acc_chk, d, -900.00, "RENT")
        tx_count += 1

    # Transfers between checking and savings
    for k in range(12):
        d = start + timedelta(days=15 * k)
        amt = 300.00
        # Checking -> Savings (withdrawal in chk, deposit in sav)
        _mk_tx(conn, acc_chk, d, -amt, "ONLINE BANKING TRANSFER TO SAV 1234")
        _mk_tx(conn, acc_sav, d, amt, "ONLINE BANKING TRANSFER FROM CHK 1234")
        tx_count += 2

    return tx_count


def seed_import_runs(conn):
    # Two runs with fake files
    for n in range(2):
        rid = str(uuid.uuid4())
        started = datetime.utcnow() - timedelta(days=7 * (n + 1))
        conn.execute(
            "INSERT INTO import_run (id, started_at, source, user_note, ai_analysis_complete) VALUES (?, ?, ?, ?, ?)",
            [rid, started, "upload:dev_seed", f"seed run {n+1}", True],
        )
        for fidx in range(2):
            fid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO import_file (id, run_id, path, type) VALUES (?, ?, ?, ?)",
                [fid, rid, f"seed_{n+1}_{fidx+1}.csv", "csv"],
            )
        # Link a handful of transactions to the run for summary
        tx_rows = conn.execute("SELECT id FROM transaction ORDER BY posted_at DESC LIMIT 10").fetchall()
        for trow in tx_rows:
            conn.execute(
                "INSERT OR IGNORE INTO transaction_ingest (tx_id, run_id) VALUES (?, ?)",
                [trow[0], rid],
            )


def main():
    if os.getenv("KASHAT_ENV", "dev") != "dev":
        print("Refusing to seed non-dev environment. Set KASHAT_ENV=dev explicitly.")
        return
    conn = get_conn()
    txc = seed_transactions(conn)
    seed_import_runs(conn)
    print(f"Seed complete. Transactions: {txc}")


if __name__ == "__main__":
    main()

