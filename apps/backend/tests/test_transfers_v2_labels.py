import json
import os
import tempfile
import unittest
from datetime import datetime


def _has_duckdb():
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_duckdb(), "duckdb not installed; skipping transfers v2 labels eval")
class TestTransfersV2Labels(unittest.TestCase):
    def test_precision_recall_on_fixture(self):
        import importlib
        from kashat.db import close as db_close, get_conn
        from kashat.transfers import suggest_transfers_v2

        tmp = tempfile.mkdtemp(prefix="ll_tr_v2_lbl_")
        os.environ["LEDGERLOOP_DATA_DIR"] = tmp
        db_close(); import kashat.db as dbmod; importlib.reload(dbmod)
        conn = get_conn()

        data = json.load(open('data/fixtures/transfers_v2_labels.json'))
        for acc in data['accounts']:
            conn.execute("INSERT OR IGNORE INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)", [acc['id'], acc['name'], acc['type'], acc['currency']])
        for t in data['transactions']:
            conn.execute(
                "INSERT INTO transaction (id, account_id, posted_at, amount, currency, description_norm, external_id, fingerprint, source_raw_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                [t['id'], t['account_id'], datetime.fromisoformat(t['date']), float(t['amount']), 'USD', t['desc'].lower(), None, t['id'], None]
            )

        suggest_transfers_v2()
        rows = conn.execute("SELECT left_tx_id, right_tx_id FROM match_transfer").fetchall()
        found = set(tuple(sorted((a,b))) for a,b in rows)
        truth = set(tuple(sorted((a,b))) for a,b in data['pairs'])
        tp = len(found & truth)
        precision = tp/len(found) if found else 1.0
        recall = tp/len(truth) if truth else 1.0
        self.assertGreaterEqual(precision, 0.95)
        self.assertGreaterEqual(recall, 0.95)


if __name__ == '__main__':
    unittest.main()

