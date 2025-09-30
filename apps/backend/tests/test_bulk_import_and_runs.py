import io
import unittest
from fastapi.testclient import TestClient
import os, tempfile

from ledgerloop.api.main import app
from ledgerloop.db import get_conn


class TestBulkImportAndRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # isolate DB for tests
        cls.tmpdir = tempfile.mkdtemp(prefix="ll_test_")
        os.environ["LEDGERLOOP_DATA_DIR"] = cls.tmpdir
        cls.client = TestClient(app)

    def setUp(self):
        # Clean basic tables
        conn = get_conn()
        for t in ("transaction_ingest","transaction_category","match_transfer","recurring_tx","transaction","raw_record","import_file","import_run"):
            try:
                conn.execute(f"DELETE FROM {t}")
            except Exception:
                pass

    def test_bulk_import_list_delete(self):
        csv1 = b"date,description,amount\n2024-01-01,Test A,-10.00\n"
        csv2 = b"date,description,amount\n2024-02-15,Test B,20.00\n"
        files = [
            ('files', ('a.csv', io.BytesIO(csv1), 'text/csv')),
            ('files', ('b.csv', io.BytesIO(csv2), 'text/csv')),
        ]
        r = self.client.post('/api/import/bulk', files=files)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        run_id = data['run_id']
        self.assertGreaterEqual(data['inserted'], 2)

        # runs list has period and tx_count
        r2 = self.client.get('/api/import/runs')
        self.assertEqual(r2.status_code, 200)
        runs = r2.json()
        self.assertTrue(any((run.get('run_id') or run.get('id')) == run_id for run in runs))

        # files view
        rf = self.client.get(f'/api/import/runs/{run_id}/files')
        self.assertEqual(rf.status_code, 200)
        files_list = rf.json()
        self.assertEqual(len(files_list), 2)

        # summary by month
        rs = self.client.get(f'/api/import/runs/{run_id}/summary')
        self.assertEqual(rs.status_code, 200)
        summary = rs.json()
        self.assertGreaterEqual(len(summary), 1)

        # delete run
        rd = self.client.delete(f'/api/import/runs/{run_id}')
        self.assertEqual(rd.status_code, 200)
        # no transactions remain
        rtx = self.client.get('/api/transactions?limit=10')
        self.assertEqual(rtx.status_code, 200)
        self.assertEqual(len(rtx.json()), 0)
