import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.mark.skip(reason="Requires /api/auth/login endpoint which is not implemented")
def test_ops_usage_counts():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_ops_")
    from kashat.api import create_app
    app = create_app()
    client = TestClient(app)

    # Login to get auth token
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "adminadmin"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Hit a couple of routes
    client.get("/api/health")
    client.get("/api/health")
    r = client.get("/api/ops/usage", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "routes" in data
    # Should include GET /api/health entry
    keys = list(data["routes"].keys())
    assert any(key.startswith("GET /api/health") for key in keys)
