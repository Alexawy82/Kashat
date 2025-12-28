import os
import tempfile
from fastapi.testclient import TestClient


def test_detect_zelle_alignment():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_zelle_")
    from kashat.api import create_app
    app = create_app()
    c = TestClient(app)
    # Seed two transactions
    csv = b"date,description,amount\n2025-01-01,Zelle from John,-5.00\n2025-01-02,Regular Coffee,-3.00\n"
    files = {"file": ("t.csv", csv, "text/csv")}
    c.post("/api/imports/csv", files=files, data={"account_id": "acc1"})
    # Preview
    r = c.post("/api/detect/zelle?commit=false")
    assert r.status_code == 200
    assert "matched" in r.json()
    # Commit via canonical
    rc = c.post("/api/detect/zelle?commit=true")
    assert rc.status_code == 200
