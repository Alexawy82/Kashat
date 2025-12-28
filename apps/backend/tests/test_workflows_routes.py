import importlib
import pytest
from fastapi import HTTPException

import kashat.api.routes.workflows as workflows


def _wf():
    importlib.reload(workflows)
    return workflows


def test_workflow_crud(db_conn):
    wf = _wf()
    payload = {
        "id": "wf1",
        "type": "IMPORT",
        "status": "idle",
        "context": {"fileName": "sample.csv"},
        "lastUpdatedAt": "2024-01-01T00:00:00Z",
    }
    saved = wf.upsert_workflow("wf1", payload)
    assert saved["id"] == "wf1"

    keys = wf.list_workflows()
    assert "wf1" in keys["keys"]

    loaded = wf.get_workflow("wf1")
    assert loaded["id"] == "wf1"
    assert loaded["type"] == "IMPORT"

    deleted = wf.delete_workflow("wf1")
    assert deleted["ok"] is True

    keys_after = wf.list_workflows()
    assert "wf1" not in keys_after["keys"]


def test_workflow_list_prefix_and_clear(db_conn):
    wf = _wf()
    wf.upsert_workflow("wf-alpha", {"id": "wf-alpha", "type": "IMPORT", "status": "idle"})
    wf.upsert_workflow("job-beta", {"id": "job-beta", "type": "IMPORT", "status": "idle"})

    keys = wf.list_workflows(prefix="wf-")
    assert keys["keys"] == ["wf-alpha"]

    cleared = wf.clear_workflows()
    assert cleared["cleared"] == 2


def test_workflow_get_missing_raises(db_conn):
    wf = _wf()
    with pytest.raises(HTTPException) as excinfo:
        wf.get_workflow("missing")
    assert excinfo.value.status_code == 404
