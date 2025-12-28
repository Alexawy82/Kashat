from datetime import datetime, UTC

import pytest

from kashat.db import get_conn
from kashat.api.routes.audit import logs as audit_logs


@pytest.fixture
def seed_audit_events(test_data_dir):
    conn = get_conn()
    conn.execute("DELETE FROM event_log")
    t1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC)
    t3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=UTC)
    rows = [
        ("e1", t1),
        ("e2", t2),
        ("e3", t3),
    ]
    for event_id, ts in rows:
        conn.execute(
            "INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [event_id, "test", "entity", "created", "{}", ts, "tester"],
        )
    return {"t1": t1, "t2": t2, "t3": t3}


def _ids(rows):
    return [row["id"] for row in rows]


def _call_audit_logs(**overrides):
    base = dict(
        entity_type=None,
        entity_id=None,
        action=None,
        start=None,
        end=None,
        limit=200,
        offset=0,
    )
    base.update(overrides)
    return audit_logs(**base)


def test_audit_logs_no_time_filters_returns_all(seed_audit_events):
    data = _call_audit_logs()
    assert _ids(data) == ["e3", "e2", "e1"]


def test_audit_logs_start_only_filters_from_start(seed_audit_events):
    data = _call_audit_logs(start=seed_audit_events["t2"])
    assert _ids(data) == ["e3", "e2"]


def test_audit_logs_end_only_filters_to_end(seed_audit_events):
    data = _call_audit_logs(end=seed_audit_events["t2"])
    assert _ids(data) == ["e2", "e1"]


def test_audit_logs_start_and_end_filters_range(seed_audit_events):
    data = _call_audit_logs(start=seed_audit_events["t2"], end=seed_audit_events["t2"])
    assert _ids(data) == ["e2"]
