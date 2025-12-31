import unittest
import os
import tempfile


def _has_duckdb():
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_duckdb(), "duckdb not installed; skipping transfers v2 eval")
class TestTransfersV2Eval(unittest.TestCase):
    def test_descriptor_pairing_precision_recall(self):
        import importlib
        from datetime import date, timedelta
        from kashat.db import close as db_close, get_conn
        from kashat.transfers import suggest_transfers_v2

        tmp = tempfile.mkdtemp(prefix="ll_tr_v2_")
        os.environ["LEDGERLOOP_DATA_DIR"] = tmp
        db_close(); import kashat.db as dbmod; importlib.reload(dbmod)
        conn = get_conn()
        # Ensure accounts exist for FK
        conn.execute("INSERT OR IGNORE INTO account (id, name, type, currency) VALUES ('acc1','A1','checking','USD')")
        conn.execute("INSERT OR IGNORE INTO account (id, name, type, currency) VALUES ('acc2','A2','savings','USD')")
        conn.execute("INSERT OR IGNORE INTO account (id, name, type, currency) VALUES ('acc3','A3','checking','USD')")

        base = date(2025, 1, 1)
        truth_pairs = []
        # 5 true pairs
        for i, last4 in enumerate(["3454", "1234", "8888", "9999", "7777"], start=1):
            # from SAV, to CHK
            desc_from = f"Online Banking transfer from SAV {last4} Confirmation# X{i}"
            desc_to = f"Online Banking transfer to CHK {last4} Confirmation# Y{i}"
            amt = 100.0 + i
            # insert
            a_id = f"a{i}"
            b_id = f"b{i}"
            conn.execute('INSERT INTO "transaction" (id, account_id, posted_at, amount, currency, description_norm, external_id, fingerprint, source_raw_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)', [a_id, "acc1", base, -amt, "USD", desc_from.lower(), None, a_id, None])
            conn.execute('INSERT INTO "transaction" (id, account_id, posted_at, amount, currency, description_norm, external_id, fingerprint, source_raw_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)', [b_id, "acc2", base + timedelta(days=1), amt, "USD", desc_to.lower(), None, b_id, None])
            truth_pairs.append({"left": min(a_id, b_id), "right": max(a_id, b_id)})
        # noise
        conn.execute('INSERT INTO "transaction" (id, account_id, posted_at, amount, currency, description_norm, external_id, fingerprint, source_raw_id, created_at) VALUES (\'n1\',\'acc3\',?, -5.0,\'USD\',\'coffee\',NULL,\'n1\',NULL,CURRENT_TIMESTAMP)', [base])

        res = suggest_transfers_v2()
        # collect suggestions
        rows = conn.execute("SELECT left_tx_id, right_tx_id, method FROM match_transfer").fetchall()
        found = set((min(a,b), max(a,b)) for a,b,_ in rows)
        truth = set((p["left"], p["right"]) for p in truth_pairs)
        tp = len(found & truth)
        precision = tp / len(found) if found else 1.0
        recall = tp / len(truth) if truth else 1.0

        self.assertEqual(precision, 1.0)
        self.assertEqual(recall, 1.0)


if __name__ == '__main__':
    unittest.main()
