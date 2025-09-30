import io
import csv
import unittest
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
import os
import tempfile

from ledgerloop.api.main import app
from ledgerloop.db import get_conn


class TestAnalyticsAndExportEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Isolate DB per test class
        cls.tmpdir = tempfile.mkdtemp(prefix="ll_test_")
        os.environ["LEDGERLOOP_DATA_DIR"] = cls.tmpdir
        cls.client = TestClient(app)

    def setUp(self):
        # Reset minimal tables for a clean slate on a fresh DB
        conn = get_conn()
        for t in (
            "event_log",
            "match_transfer",
            "transaction_category",
            "transaction",
            "category",
            "recurring_series",
            "recurring_tx",
        ):
            try:
                conn.execute(f"DELETE FROM {t}")
            except Exception:
                pass
        # Seed account + category
        conn.execute(
            "INSERT OR IGNORE INTO account (id, name, type, currency) VALUES ('acc1','Checking','checking','USD')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO category (id, name) VALUES ('cat1','Groceries')"
        )
        # Seed transactions across two months
        base = date.today().replace(day=1)
        last_month = (base - timedelta(days=1)).replace(day=1)
        rows = [
            ("t1", "acc1", last_month, -50.0, "USD", "STORE A"),
            ("t2", "acc1", last_month, -75.0, "USD", "STORE B"),
            ("t3", "acc1", base, -120.0, "USD", "STORE A"),
            ("t4", "acc1", base, 1000.0, "USD", "PAYROLL"),
            ("t5", "acc1", base, -20.0, "USD", "TRANSFER OUT"),
        ]
        for rid, acc, d, amt, curr, desc in rows:
            conn.execute(
                "INSERT INTO transaction (id, account_id, posted_at, amount, currency, description_norm, fingerprint, created_at) VALUES (?,?,?,?,?,?,?,?)",
                [rid, acc, d, amt, curr, desc, f"fp_{rid}", datetime.utcnow()],
            )
        # Categorize some
        conn.execute("INSERT INTO transaction_category (tx_id, category_id) VALUES ('t1','cat1'), ('t3','cat1')")
        # Mark t5 as transfer (decided)
        conn.execute(
            "INSERT INTO match_transfer (left_tx_id, right_tx_id, score, method, decided_at) VALUES ('t5','x', 0.9, 'heuristic', ?)",
            [datetime.utcnow()],
        )

    def test_analytics_summary_excludes_transfers_by_default(self):
        r = self.client.get("/api/analytics/summary")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        # totals should exclude the transfer t5
        self.assertIn("totals", data)
        totals = data["totals"]
        # spend = 50 + 75 + 120 = 245
        self.assertAlmostEqual(totals["spend"], 245.0, places=2)
        # income = 1000
        self.assertAlmostEqual(totals["income"], 1000.0, places=2)
        # net = 1000 - 245
        self.assertAlmostEqual(totals["net"], 755.0, places=2)

    def test_analytics_summary_include_transfers(self):
        r = self.client.get("/api/analytics/summary?includeTransfers=true")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        totals = data["totals"]
        # include transfer spend of 20 as well -> spend 265, net 735
        self.assertAlmostEqual(totals["spend"], 265.0, places=2)
        self.assertAlmostEqual(totals["net"], 735.0, places=2)

    def test_analytics_predictions_structure(self):
        r = self.client.get("/api/analytics/predictions")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("budgetRisk", data)
        self.assertIn("savingsOps", data)
        self.assertIn("recurringForecast", data)
        # Ensure deterministic types
        if data["budgetRisk"]:
            item = data["budgetRisk"][0]
            self.assertIn("category", item)
            self.assertIn("deltaPct", item)

    def test_export_csv_streaming_and_headers(self):
        today = date.today().isoformat()
        r = self.client.get(f"/api/export/csv?from={today}&to={today}&onlyBusiness=false&includeTransfers=false")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers.get("content-type", ""))
        cd = r.headers.get("content-disposition", "")
        self.assertIn("transactions_", cd)
        # Read small streamed payload
        buf = io.StringIO(r.text)
        rdr = csv.reader(buf)
        rows = list(rdr)
        self.assertGreaterEqual(len(rows), 1)  # header + data
