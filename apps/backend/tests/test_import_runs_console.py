import io
import os
import tempfile
import unittest


class TestImportRunsConsole(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from kashat.api import create_app
        self.client = TestClient(create_app())

    def test_list_files_summary_bulk_reprocess_delete(self):
        # Prepare two small CSVs as uploads
        csv1 = io.BytesIO(b"date,amount,description\n2024-01-02,-12.34,NETFLIX\n2024-01-03,1000,PAYROLL\n")
        csv2 = io.BytesIO(b"date,amount,description\n2024-02-10,-900,RENT\n2024-02-12,900,TRANSFER FROM CHK 1234\n")
        files = [
            ('files', ('a.csv', csv1, 'text/csv')),
            ('files', ('b.csv', csv2, 'text/csv')),
        ]
        r = self.client.post('/api/imports/bulk', files=files, data={'enable_ai':'false'})
        assert r.status_code == 200, r.text
        data = r.json()
        run_id = data['run_id']

        # List runs includes representative fields
        r2 = self.client.get('/api/imports/runs')
        assert r2.status_code == 200
        runs = r2.json()
        assert any(x['id'] == run_id for x in runs)
        row = [x for x in runs if x['id'] == run_id][0]
        assert 'file_count' in row and 'tx_count' in row and 'status' in row and 'summary_available' in row

        # Files and summary endpoints
        rf = self.client.get(f'/api/imports/runs/{run_id}/files')
        assert rf.status_code == 200
        files_json = rf.json()
        assert isinstance(files_json, list)

        rs = self.client.get(f'/api/imports/runs/{run_id}/summary')
        assert rs.status_code == 200
        summary = rs.json()
        assert isinstance(summary, list)

        # Reprocess
        rr = self.client.post(f'/api/imports/runs/{run_id}/reprocess')
        assert rr.status_code == 200

        # Delete run
        rd = self.client.delete(f'/api/imports/runs/{run_id}')
        assert rd.status_code == 200
        # Ensure it's gone
        r3 = self.client.get('/api/imports/runs')
        assert all(x['id'] != run_id for x in r3.json())
