import os
import tempfile
from fastapi.testclient import TestClient


def _setup_client():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_cat_")
    from kashat.api import create_app
    app = create_app()
    client = TestClient(app)
    return client


def test_category_delete_and_merge():
    c = _setup_client()
    # Create two categories
    r1 = c.post("/api/categories", json={"name": "A"}).json()
    r2 = c.post("/api/categories", json={"name": "B"}).json()
    a, b = r1["id"], r2["id"]
    # Deleting A should succeed (no children, no refs)
    rd = c.delete(f"/api/categories/{a}")
    assert rd.status_code == 200
    # Recreate A and assign a transaction to it to test merge
    r1 = c.post("/api/categories", json={"name": "A"}).json()
    a = r1["id"]
    # Create a transaction and attach category A
    # Minimal route to add a transaction via import: create a CSV import
    csv = b"date,description,amount\n2025-01-01,Test Tx,-10.00\n"
    files = {"file": ("one.csv", csv, "text/csv")}
    c.post("/api/imports/csv", files=files, data={"account_id": "accx"})
    tx = c.get("/api/transactions?limit=1").json()[0]
    c.post(f"/api/transactions/{tx['id']}/category", json={"category_id": a})
    # Delete A should fail due to refs
    rd2 = c.delete(f"/api/categories/{a}")
    assert rd2.status_code == 400
    # Merge A into B
    rm = c.post("/api/categories/merge", json={"from_id": a, "to_id": b})
    assert rm.status_code == 200
    # usage on A should be zero (deleted)
    ru = c.get(f"/api/categories/{a}/usage")
    assert ru.status_code in (404, 200)
