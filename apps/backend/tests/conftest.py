"""
Shared pytest fixtures for LedgerLoop API tests
"""

import os
import tempfile
import importlib
from datetime import date, timedelta, datetime, UTC
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary data directory for tests"""
    tmpdir = tempfile.mkdtemp(prefix="ll_test_")
    os.environ["LEDGERLOOP_DATA_DIR"] = tmpdir
    return tmpdir


@pytest.fixture(scope="session")
def test_app(test_data_dir):
    """Create the FastAPI app for testing"""
    from kashat.api import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(test_app):
    """Create a test client"""
    return TestClient(test_app)


@pytest.fixture(scope="session")
def auth_token(client):
    """Get authentication token for API tests"""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminadmin"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    """Get authentication headers for API tests"""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


@pytest.fixture
def authenticated_client(client, auth_headers):
    """
    Create a wrapper around the test client that includes auth headers.
    Usage:
        def test_something(authenticated_client):
            response = authenticated_client.get("/api/transactions")
    """
    class AuthenticatedClient:
        def __init__(self, client, headers):
            self._client = client
            self._headers = headers

        def request(self, method, url, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._headers)
            return self._client.request(method, url, headers=headers, **kwargs)

        def get(self, url, **kwargs):
            return self.request("GET", url, **kwargs)

        def post(self, url, **kwargs):
            return self.request("POST", url, **kwargs)

        def put(self, url, **kwargs):
            return self.request("PUT", url, **kwargs)

        def patch(self, url, **kwargs):
            return self.request("PATCH", url, **kwargs)

        def delete(self, url, **kwargs):
            return self.request("DELETE", url, **kwargs)

    return AuthenticatedClient(client, auth_headers)


@pytest.fixture
def db_conn(tmp_path, monkeypatch):
    """Isolated DuckDB connection for unit tests (no TestClient)."""
    monkeypatch.setenv("LEDGERLOOP_DATA_DIR", str(tmp_path))
    import kashat.db as dbmod
    dbmod.close()
    importlib.reload(dbmod)
    conn = dbmod.get_conn()
    try:
        yield conn
    finally:
        dbmod.close()


@pytest.fixture
def sample_transactions():
    """Small, varied transaction set for deterministic unit tests."""
    base = date(2024, 1, 1)
    return [
        {"id": "t1", "account_id": "acc1", "posted_at": base, "amount": -12.34, "currency": "USD", "description_norm": "coffee shop"},
        {"id": "t2", "account_id": "acc1", "posted_at": base + timedelta(days=1), "amount": -45.00, "currency": "USD", "description_norm": "grocery mart"},
        {"id": "t3", "account_id": "acc2", "posted_at": base + timedelta(days=2), "amount": 1000.00, "currency": "USD", "description_norm": "payroll"},
    ]


@pytest.fixture
def seed_transactions(db_conn):
    """Helper to insert accounts + transactions into the isolated DB."""
    def _seed(rows):
        accounts = {row["account_id"] for row in rows}
        for acc in accounts:
            db_conn.execute(
                "INSERT OR IGNORE INTO account (id, name, type, currency) VALUES (?, ?, ?, ?)",
                [acc, acc, "checking", "USD"],
            )
        for row in rows:
            db_conn.execute(
                "INSERT INTO [transaction] (id, account_id, posted_at, amount, currency, description_norm, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    row["id"],
                    row["account_id"],
                    row["posted_at"],
                    row["amount"],
                    row.get("currency", "USD"),
                    row["description_norm"],
                    f"fp_{row['id']}",
                    datetime.now(UTC),
                ],
            )
        return rows

    return _seed
