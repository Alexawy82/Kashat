import importlib

import kashat.api.routes.imports as imports


def _imports():
    importlib.reload(imports)
    return imports


def test_parse_import_creates_run_and_file(db_conn):
    imp = _imports()
    req = imp.ParseRequest(
        account_id="acc1",
        source="workflow:test",
        user_note="unit test",
        file_info=imp.ParseFileInfo(
            name="sample.csv",
            type="csv",
            size=123,
            hash="hash123",
        ),
    )
    res = imp.parse_import(req)
    assert res["run_id"]
    assert res["file_id"]
    assert res["account_id"] == "acc1"
    assert res["status"] == "created"

    run = db_conn.execute(
        "SELECT id FROM import_run WHERE id = ?",
        [res["run_id"]],
    ).fetchone()
    assert run is not None

    file_row = db_conn.execute(
        "SELECT id FROM import_file WHERE id = ?",
        [res["file_id"]],
    ).fetchone()
    assert file_row is not None


def test_parse_import_existing_run(db_conn):
    imp = _imports()
    first = imp.parse_import(imp.ParseRequest())
    res = imp.parse_import(imp.ParseRequest(run_id=first["run_id"]))
    assert res["run_id"] == first["run_id"]
    assert res["status"] == "existing"
