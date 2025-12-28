import unittest
from datetime import date
from kashat.transfers import (
    jaccard_similarity,
    _canonical_pair,
    _score_pair,
    suggest_transfers,
    list_transfers,
    confirm_transfer,
    reject_transfer,
)


class TestTransfers(unittest.TestCase):
    def test_jaccard_similarity(self):
        self.assertAlmostEqual(jaccard_similarity("transfer to savings", "transfer from checking"), 1/5, places=3)
        self.assertEqual(jaccard_similarity("", ""), 1.0)
        self.assertEqual(jaccard_similarity("abcd", ""), 0.0)
        self.assertGreater(jaccard_similarity("transfer to savings", "transfer savings"), 0.4)


def test_transfer_helpers_and_flow(db_conn, seed_transactions):
    rows = [
        {"id": "t1", "account_id": "acc1", "posted_at": date(2024, 1, 1), "amount": -50.0, "currency": "USD", "description_norm": "transfer savings 1234"},
        {"id": "t2", "account_id": "acc2", "posted_at": date(2024, 1, 2), "amount": 50.0, "currency": "USD", "description_norm": "transfer savings 1234"},
        {"id": "t3", "account_id": "acc1", "posted_at": date(2024, 1, 3), "amount": -25.0, "currency": "USD", "description_norm": "transfer savings 9999"},
        {"id": "t4", "account_id": "acc2", "posted_at": date(2024, 1, 4), "amount": 25.0, "currency": "USD", "description_norm": "transfer savings 9999"},
    ]
    seed_transactions(rows)

    left, right = _canonical_pair("b", "a")
    assert (left, right) == ("a", "b")
    assert _score_pair(1, 3, 1.0) > 0.5

    result = suggest_transfers(max_days=3, amount_tolerance=0.1, limit=10)
    assert result["suggested"] >= 2

    pending = list_transfers(status="pending")
    assert len(pending) >= 2

    confirmed = confirm_transfer("t1", "t2")
    assert confirmed["left_tx_id"] in ("t1", "t2")
    assert confirmed["right_tx_id"] in ("t1", "t2")
    assert confirmed["group_id"]

    confirmed_rows = list_transfers(status="confirmed")
    assert any(r["left_tx_id"] == confirmed["left_tx_id"] for r in confirmed_rows)

    rejected = reject_transfer("t3", "t4")
    assert rejected["left_tx_id"] in ("t3", "t4")

    remaining = db_conn.execute(
        "SELECT COUNT(*) FROM match_transfer WHERE left_tx_id IN ('t3','t4') OR right_tx_id IN ('t3','t4')"
    ).fetchone()[0]
    assert remaining == 0


if __name__ == "__main__":
    unittest.main()
