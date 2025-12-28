import os
import tempfile
from fastapi.testclient import TestClient


def test_schema_version_table_exists():
    os.environ["LEDGERLOOP_DATA_DIR"] = tempfile.mkdtemp(prefix="ll_schema_")
    from kashat.api import create_app
    from kashat.db import get_conn
    app = create_app()
    _ = TestClient(app)
    conn = get_conn()
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    assert row is not None

