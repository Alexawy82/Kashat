import os
import tempfile
from fastapi.testclient import TestClient


def test_analytics_dashboard_exists():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_dash_")
    from kashat.api import create_app
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/analytics/dashboard")
    assert r.status_code == 200
    data = r.json()
    for key in ("summary", "monthly", "merchants", "cashflow"):
        assert key in data

