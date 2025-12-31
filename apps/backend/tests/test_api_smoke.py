import os
import tempfile
import unittest
from io import BytesIO


class TestAPISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_api_")
        from fastapi.testclient import TestClient
        from kashat.api import create_app
        cls.app = create_app()
        cls.client = TestClient(cls.app)
        # Authenticate and get token for protected endpoints
        login_resp = cls.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "adminadmin"}
        )
        if login_resp.status_code == 200:
            cls.token = login_resp.json().get("access_token")
            cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}
        else:
            cls.token = None
            cls.auth_headers = {}

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")

    def test_import_csv_and_list_transactions(self):
        # create categories so inline category ops can succeed later
        self.client.post("/api/categories", json={"name": "General"}, headers=self.auth_headers)
        with open("data/fixtures/sample_bank.csv", "rb") as f:
            files = {"file": ("sample_bank.csv", f.read(), "text/csv")}
        r = self.client.post("/api/imports/csv", files=files, data={"account_id": "acc1"}, headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertGreaterEqual(j.get("inserted", 0), 1)

        r2 = self.client.get("/api/transactions?limit=10", headers=self.auth_headers)
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        # API returns paginated response {items: [...], total, limit, offset, total_pages}
        rows = data.get("items", data) if isinstance(data, dict) else data
        self.assertIsInstance(rows, list)
        self.assertGreaterEqual(len(rows), 1)

    def test_export_csv(self):
        r = self.client.get("/api/export/transactions.csv", headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers.get("content-type", ""))
        self.assertIn("id,account_id,posted_at,amount", r.text.splitlines()[0])

    def test_transfers_toggle_include(self):
        # import second account to allow pairing
        with open("data/fixtures/sample_bank2.csv", "rb") as f:
            files = {"file": ("sample_bank2.csv", f.read(), "text/csv")}
        r = self.client.post("/api/imports/csv", files=files, data={"account_id": "acc2"}, headers=self.auth_headers)
        self.assertEqual(r.status_code, 200)
        # suggest basic pairs
        self.client.post("/api/transfers/suggest_v2", headers=self.auth_headers)
        # list pending and confirm first if exists
        rp = self.client.get("/api/transfers?status=pending", headers=self.auth_headers).json()
        if rp:
            p = rp[0]
            self.client.post("/api/transfers/confirm", json={"left_tx_id": p["left_tx_id"], "right_tx_id": p["right_tx_id"]}, headers=self.auth_headers)
        rc = self.client.get("/api/transfers?status=confirmed", headers=self.auth_headers).json()
        if rc and rc[0].get("group_id"):
            gid = rc[0]["group_id"]
            r = self.client.post(f"/api/transfers/group/{gid}/analytics?include=true", headers=self.auth_headers)
            self.assertEqual(r.status_code, 200)

    def test_detect_income_adjustments(self):
        # Create a couple of direct tx rows via CSV import with CASHBACK and PAYROLL words
        buf = BytesIO()
        buf.write(b"date,description,amount,currency\n")
        buf.write(b"2025-01-01,employer payroll,1000.00,USD\n")
        buf.write(b"2025-01-02,cashback credit,5.00,USD\n")
        files = {"file": ("tmp.csv", buf.getvalue(), "text/csv")}
        self.client.post("/api/imports/csv", files=files, data={"account_id": "acc3"}, headers=self.auth_headers)
        # detect and commit
        self.client.post("/api/detect/income?commit=true", headers=self.auth_headers)
        self.client.post("/api/detect/adjustments?commit=true", headers=self.auth_headers)
        # check flags present
        r = self.client.get("/api/transactions?limit=50", headers=self.auth_headers)
        data = r.json()
        rows = data.get("items", data) if isinstance(data, dict) else data
        flags = [(x.get("is_income"), x.get("is_adjustment")) for x in rows]
        self.assertIn((True, False), flags)
        self.assertIn((False, True), flags)


if __name__ == '__main__':
    unittest.main()
