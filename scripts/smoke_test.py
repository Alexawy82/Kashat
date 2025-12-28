#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from requests import exceptions as req_exc


DEFAULT_BASE = "http://127.0.0.1:8000/api"
DEFAULT_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "sample_bank.csv"
START_CMD = "make run-backend"


def _get_base_url() -> str:
    base = os.getenv("KASHAT_SMOKE_API", DEFAULT_BASE).rstrip("/")
    return base


def _get_fixture_path() -> Path:
    raw = os.getenv("KASHAT_SMOKE_FIXTURE")
    if raw:
        return Path(raw).expanduser()
    return DEFAULT_FIXTURE


def _request_json(
    method: str,
    url: str,
    session: requests.Session,
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        resp = session.request(method, url, **kwargs)
    except req_exc.ConnectionError as exc:
        raise RuntimeError(f"Backend not running; start it with: {START_CMD}") from exc
    if not resp.ok:
        raise RuntimeError(f"{method} {url} failed: {resp.status_code} {resp.text[:200]}")
    try:
        return resp.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {url} did not return JSON") from exc


def _import_csv(
    base_url: str,
    fixture: Path,
    session: requests.Session,
    account_id: Optional[str],
) -> Dict[str, Any]:
    if not fixture.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture}")
    data = {
        "enable_ai": "false",
        "enable_workflow": "false",
    }
    if account_id:
        data["account_id"] = account_id
    with fixture.open("rb") as handle:
        files = {"file": (fixture.name, handle, "text/csv")}
        return _request_json("POST", f"{base_url}/imports/csv", session, data=data, files=files)


def _detect_preview(
    base_url: str,
    session: requests.Session,
    endpoint: str,
) -> Dict[str, Any]:
    return _request_json("POST", f"{base_url}{endpoint}", session)


def _analytics_summary(base_url: str, session: requests.Session) -> Dict[str, Any]:
    return _request_json("GET", f"{base_url}/analytics/summary", session)


def _export_preset(base_url: str, session: requests.Session) -> Tuple[str, str]:
    try:
        resp = session.post(f"{base_url}/export", params={"format": "csv"})
    except req_exc.ConnectionError as exc:
        raise RuntimeError(f"Backend not running; start it with: {START_CMD}") from exc
    if not resp.ok:
        raise RuntimeError(f"POST {base_url}/export failed: {resp.status_code} {resp.text[:200]}")
    content_type = resp.headers.get("content-type", "")
    text = resp.text
    first_line = text.splitlines()[0] if text else ""
    return content_type, first_line


def main() -> int:
    base_url = _get_base_url()
    fixture = _get_fixture_path()
    account_id = os.getenv("KASHAT_SMOKE_ACCOUNT_ID")

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    print("LedgerLoop Smoke Test")
    print(f"- API base: {base_url}")
    print(f"- Fixture: {fixture}")

    try:
        import_result = _import_csv(base_url, fixture, session, account_id)
        run_id = import_result.get("run_id")
        inserted = int(import_result.get("inserted") or 0)
        deduped = int(import_result.get("deduped") or 0)
        raw = int(import_result.get("raw") or 0)
        print(f"Import: run_id={run_id} inserted={inserted} deduped={deduped} raw={raw}")
    except Exception as exc:
        print(f"FAIL import: {exc}")
        return 1

    try:
        zelle = _detect_preview(base_url, session, "/detect/zelle?commit=false")
        income = _detect_preview(base_url, session, "/detect/income?commit=false")
        adjustments = _detect_preview(base_url, session, "/detect/adjustments?commit=false")
        print(f"Detect: zelle={zelle.get('matched')} income={income.get('matched')} adjustments={adjustments.get('matched')}")
    except Exception as exc:
        print(f"FAIL detect: {exc}")
        return 1

    try:
        summary = _analytics_summary(base_url, session)
        totals = summary.get("totals") or {}
        print(f"Analytics: income={totals.get('income')} spend={totals.get('spend')} net={totals.get('net')}")
    except Exception as exc:
        print(f"FAIL analytics: {exc}")
        return 1

    try:
        content_type, first_line = _export_preset(base_url, session)
        print(f"Export: content-type={content_type} columns={first_line}")
        if "text/csv" not in content_type:
            raise RuntimeError(f"Unexpected content-type: {content_type}")
        if "id,account_id" not in first_line:
            raise RuntimeError(f"Unexpected CSV header: {first_line}")
    except Exception as exc:
        print(f"FAIL export: {exc}")
        return 1

    print("PASS smoke test (no AI, no realtime, no auth)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
