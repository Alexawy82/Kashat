import unittest
from datetime import date, timedelta
from kashat.recurring import (
    cadence_from_intervals,
    detect_recurring_candidates,
    Tx,
    _next_date,
    suggest_recurring,
    list_recurring,
    confirm_series,
    reject_series,
    dedupe_recurring_series,
    normalize_recurring_key,
)


class TestRecurring(unittest.TestCase):
    def test_cadence_from_intervals(self):
        self.assertEqual(cadence_from_intervals([7, 7, 8]), "weekly")
        self.assertEqual(cadence_from_intervals([28, 30, 31]), "monthly")
        self.assertIsNone(cadence_from_intervals([10, 15, 20]))

    def test_detect_candidates(self):
        base = date(2024, 1, 1)
        txs = [
            Tx(id=f"t{i}", account_id="a1", posted_at=base + timedelta(days=30 * i), amount=-10.00, description_norm="netflix")
            for i in range(3)
        ]
        cands = detect_recurring_candidates(txs)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["cadence"], "monthly")
        self.assertEqual(cands[0]["anchor_day"], 1)

    def test_recurring_key_normalizes_p2p_noise(self):
        raw = "pmnt sent 1004 venmo *mai elm visa direct ny"
        key = normalize_recurring_key(raw, amount=-20.0)
        self.assertEqual(key, "venmo mai elm")

        raw2 = "pmnt sent 0717 cash app*marwan oakland ca 40593651983163602363605"
        key2 = normalize_recurring_key(raw2, amount=-200.0)
        self.assertEqual(key2, "cashapp marwan")

        raw3 = "pmnt sent 0930 wuvisaaft 800-325-6000 co 24692165273109014555893"
        key3 = normalize_recurring_key(raw3, amount=-508.99)
        self.assertEqual(key3, "western_union")


def test_detect_candidates_groups_noisy_p2p():
    base = date(2024, 1, 1)
    txs = [
        Tx(id="v1", account_id="a1", posted_at=base, amount=-20.0, description_norm="pmnt sent 0101 venmo *mai elm visa direct ny"),
        Tx(id="v2", account_id="a1", posted_at=date(2024, 2, 1), amount=-20.0, description_norm="pmnt sent 0201 venmo *mai elm visa direct ny"),
        Tx(id="v3", account_id="a1", posted_at=date(2024, 3, 1), amount=-20.0, description_norm="pmnt sent 0301 venmo *mai elm visa direct ny"),
    ]
    cands = detect_recurring_candidates(txs, min_occurrences=3, tol=0.01)
    assert len(cands) == 1
    assert cands[0]["desc"] == "venmo mai elm"
    assert cands[0]["cadence"] == "monthly"


def test_next_date_helper():
    base = date(2024, 1, 1)
    assert _next_date(base, "weekly") == date(2024, 1, 8)
    assert _next_date(base, "biweekly") == date(2024, 1, 15)
    assert _next_date(base, "monthly") == date(2024, 1, 31)


def test_recurring_db_flow(db_conn, seed_transactions):
    rows = [
        {"id": "r1", "account_id": "acc1", "posted_at": date(2024, 1, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "r2", "account_id": "acc1", "posted_at": date(2024, 2, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "r3", "account_id": "acc1", "posted_at": date(2024, 3, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
    ]
    seed_transactions(rows)

    res = suggest_recurring(min_occurrences=3, tol=0.02, limit=100)
    assert res["created"] == 1

    pending = list_recurring(status="pending")
    assert len(pending) == 1
    series_id = pending[0]["id"]

    confirmed = confirm_series(series_id)
    assert confirmed["status"] == "confirmed"

    rejected = reject_series(series_id)
    assert rejected["status"] == "rejected"


def test_suggest_recurring_idempotent(db_conn, seed_transactions):
    rows = [
        {"id": "i1", "account_id": "acc1", "posted_at": date(2024, 1, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "i2", "account_id": "acc1", "posted_at": date(2024, 2, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "i3", "account_id": "acc1", "posted_at": date(2024, 3, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
    ]
    seed_transactions(rows)

    res1 = suggest_recurring(min_occurrences=3, tol=0.02, limit=100)
    assert res1["created"] == 1

    res2 = suggest_recurring(min_occurrences=3, tol=0.02, limit=100)
    assert res2["created"] == 0

    pending = list_recurring(status="pending")
    assert len(pending) == 1


def test_recurring_dedupe_merges_memberships(db_conn, seed_transactions):
    rows = [
        {"id": "d1", "account_id": "acc1", "posted_at": date(2024, 1, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "d2", "account_id": "acc1", "posted_at": date(2024, 2, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
        {"id": "d3", "account_id": "acc1", "posted_at": date(2024, 3, 1), "amount": -9.99, "currency": "USD", "description_norm": "netflix"},
    ]
    seed_transactions(rows)

    # Manually insert duplicate pending series for the same key.
    db_conn.execute(
        "INSERT INTO recurring_series (id, name, cadence, anchor_day, amount_mean, amount_sd, status, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ["s1", "netflix", "monthly", 1, -9.99, 0.0, "pending", None],
    )
    db_conn.execute(
        "INSERT INTO recurring_series (id, name, cadence, anchor_day, amount_mean, amount_sd, status, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ["s2", "netflix", "monthly", 1, -9.99, 0.0, "pending", None],
    )
    db_conn.execute("INSERT INTO recurring_tx (series_id, tx_id) VALUES (?, ?)", ["s1", "d1"])
    db_conn.execute("INSERT INTO recurring_tx (series_id, tx_id) VALUES (?, ?)", ["s1", "d2"])
    db_conn.execute("INSERT INTO recurring_tx (series_id, tx_id) VALUES (?, ?)", ["s2", "d3"])

    removed = dedupe_recurring_series(db_conn)
    assert removed == 1

    remaining = db_conn.execute("SELECT COUNT(*) FROM recurring_series").fetchone()[0]
    assert remaining == 1

    # Memberships should be merged onto the kept series.
    merged = db_conn.execute("SELECT COUNT(*) FROM recurring_tx").fetchone()[0]
    assert merged == 3


if __name__ == "__main__":
    unittest.main()
