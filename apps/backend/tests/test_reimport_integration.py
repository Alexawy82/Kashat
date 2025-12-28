import os
import tempfile
import unittest


def _has_duckdb():
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_has_duckdb(), "duckdb not installed; skipping integration test")
class TestReimportIntegration(unittest.TestCase):
    def test_reimport_idempotent(self):
        import importlib
        from kashat.db import close as db_close
        from kashat.ingest_csv import import_csv_upload
        from kashat.db import get_conn

        tmp = tempfile.mkdtemp(prefix="ll_db_")
        os.environ["LEDGERLOOP_DATA_DIR"] = tmp
        # reset connection
        db_close()
        import kashat.db as dbmod
        importlib.reload(dbmod)

        with open("data/fixtures/sample_bank.csv", "rb") as f:
            import_csv_upload(f.read(), "sample_bank.csv", account_id="acc1")
        with open("data/fixtures/sample_bank.csv", "rb") as f:
            import_csv_upload(f.read(), "sample_bank.csv", account_id="acc1")

        conn = get_conn()
        cnt = conn.execute("SELECT COUNT(*) FROM transaction").fetchone()[0]
        # Expect 6 unique transactions from sample_bank.csv
        self.assertEqual(cnt, 6)


if __name__ == "__main__":
    unittest.main()

