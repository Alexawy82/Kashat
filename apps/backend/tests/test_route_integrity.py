from __future__ import annotations

from collections import defaultdict


def test_no_duplicate_route_registrations():
    from kashat.api import create_app

    app = create_app()

    seen = defaultdict(list)
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = tuple(sorted(getattr(r, "methods", []) or []))
        if not path or not methods:
            continue
        key = (path, methods)
        seen[key].append(getattr(r, "name", None))

    dups = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dups, f"Duplicate routes found: {dups}"


def test_expected_import_routes_present():
    from kashat.api import create_app

    app = create_app()
    paths = set()
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        for m in methods:
            paths.add((m, path))

    for method, path in [
        ("POST", "/api/imports/csv"),
        ("POST", "/api/imports/pdf"),
        ("POST", "/api/imports/bulk"),
        ("GET", "/api/imports/report/{run_id}"),
        ("GET", "/api/imports/{run_id}/ai-analysis"),
        ("POST", "/api/imports/suggest-rules"),
    ]:
        assert (method, path) in paths


def test_expected_rules_routes_present():
    from kashat.api import create_app

    app = create_app()
    paths = set()
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        for m in methods:
            paths.add((m, path))

    for method, path in [
        ("GET", "/api/rules"),
        ("POST", "/api/rules"),
        ("PATCH", "/api/rules/{rule_id}"),
        ("DELETE", "/api/rules/{rule_id}"),
    ]:
        assert (method, path) in paths
