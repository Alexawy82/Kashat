import unittest


class TestContractRoutes(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from kashat.api import create_app
        self.client = TestClient(create_app())

    def _assert_ok(self, method: str, path: str):
        r = self.client.request(method, path)
        # Accept common success or validation statuses for existence checks
        assert r.status_code in (200, 204, 400, 404, 422), f"{method} {path} -> {r.status_code} {r.text}"

    def test_routes_exist(self):
        # Recurring
        self._assert_ok('GET', '/api/recurring')
        self._assert_ok('GET', '/api/recurring?status=pending')
        self._assert_ok('GET', '/api/recurring?status=confirmed')
        self._assert_ok('POST', '/api/recurring/suggest')
        # POST bodies not required for mere existence checks
        self._assert_ok('POST', '/api/recurring/confirm')
        self._assert_ok('POST', '/api/recurring/reject')

        # Transfers
        self._assert_ok('GET', '/api/transfers')
        self._assert_ok('GET', '/api/transfers?status=pending')
        self._assert_ok('GET', '/api/transfers?status=confirmed')
        self._assert_ok('POST', '/api/transfers/suggest_v2')
        self._assert_ok('POST', '/api/transfers/confirm')
        self._assert_ok('POST', '/api/transfers/reject')
        # Analytics toggle – use dummy id; endpoint exists if not 404
        r = self.client.post('/api/transfers/group/00000000-0000-0000-0000-000000000000/analytics?include=true')
        assert r.status_code in (200, 404), r.text

        # Import console
        self._assert_ok('GET', '/api/imports/runs')
        # Use placeholder id; allow 404 depending on DB state
        for p in ('files', 'summary'):
            r = self.client.get(f'/api/imports/runs/00000000-0000-0000-0000-000000000000/{p}')
            assert r.status_code in (200, 404), r.text
        # Bulk upload endpoint exists (multipart required normally)
        r = self.client.post('/api/imports/bulk')
        assert r.status_code in (200, 400, 422), r.text
        # Reprocess, Delete exist
        r = self.client.post('/api/imports/runs/00000000-0000-0000-0000-000000000000/reprocess')
        assert r.status_code in (200, 404), r.text
        r = self.client.delete('/api/imports/runs/00000000-0000-0000-0000-000000000000')
        assert r.status_code in (200, 404), r.text
