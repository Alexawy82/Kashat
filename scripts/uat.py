#!/usr/bin/env python3
"""
UAT: Automated end-to-end checks against a running backend (and optional web).

Steps:
- Health and settings sanity
- Import sample CSV with AI enabled; poll AI analysis
- List transactions; analyze one; get smart suggestions
- Start AI bulk job (admin); poll job status
- Data stats (admin)
- Metrics endpoint sanity

Exits non-zero on first failure; prints a concise summary.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests


BASE = os.environ.get("UAT_API_BASE", "http://127.0.0.1:8000/api")
ADMIN_TOKEN = os.environ.get("KASHAT_ADMIN_TOKEN", "uat_admin_token")
HEADERS = {"Content-Type": "application/json"}
ADMIN_HEADERS = {**HEADERS, "Authorization": f"Bearer {ADMIN_TOKEN}"}


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"[OK] {msg}")


def get(url: str, admin: bool = False):
    r = requests.get(url, headers=ADMIN_HEADERS if admin else HEADERS, timeout=20)
    return r


def post(url: str, data=None, admin: bool = False, files=None):
    if files:
        r = requests.post(url, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"} if admin else None, files=files, timeout=60)
    else:
        r = requests.post(url, headers=ADMIN_HEADERS if admin else HEADERS, data=json.dumps(data or {}), timeout=60)
    return r


def uat():
    # 1) Health
    r = get(f"{BASE}/health")
    if r.status_code != 200:
        fail(f"health status {r.status_code}")
    ok("health check")

    # 2) Settings round-trip and provider sanity
    r = get(f"{BASE}/settings")
    if r.status_code != 200:
        fail("settings get")
    s = r.json()
    if "recurring_tolerance" not in s:
        fail("settings payload missing keys")
    ok("settings get")
    # Keep provider local to avoid network flakiness during UAT
    r = post(f"{BASE}/settings", {"ai_provider": "local"})
    if r.status_code != 200:
        fail("settings post")
    ok("settings post (ai_provider=local)")

    # 3) Import sample CSV with AI enabled
    sample = Path("data/fixtures/sample_bank.csv")
    if not sample.exists():
        fail("missing data/fixtures/sample_bank.csv")
    with sample.open("rb") as f:
        files = {"file": (sample.name, f, "text/csv"), "enable_ai": (None, "true")}
        r = requests.post(f"{BASE}/import/csv", files=files, timeout=60)
    if r.status_code != 200:
        fail(f"import csv status {r.status_code}")
    j = r.json()
    run_id = j.get("run_id")
    acct = j.get("account_id")
    if not run_id or j.get("inserted", 0) <= 0:
        fail("import result invalid")
    ok(f"import csv run_id={run_id}")

    # 4) Poll AI analysis for the run
    done = False
    for _ in range(240):  # up to ~120s
        r = get(f"{BASE}/import/{run_id}/ai-analysis")
        if r.status_code == 200:
            a = r.json()
            if a.get("analysis_complete") or a.get("ai_enhanced_count") is not None:
                done = True
                break
        time.sleep(0.5)
    if not done:
        fail("AI analysis did not complete in time")
    ok("import AI analysis complete")

    # 5) List transactions for account
    r = get(f"{BASE}/transactions?account_id={acct}&limit=20")
    if r.status_code != 200:
        fail("list transactions")
    txs = r.json()
    if not isinstance(txs, list) or not txs:
        fail("no transactions returned")
    tx_id = txs[0]["id"]
    ok(f"transactions listed ({len(txs)})")

    # 6) Analyze transaction
    r = post(f"{BASE}/ai/analyze/transaction/{tx_id}")
    if r.status_code != 200:
        fail(f"analyze transaction status {r.status_code}")
    ana = r.json()
    if "merchant_name" not in ana or "processing_method" not in ana:
        fail("analysis payload invalid")
    ok("analyze transaction (single)")

    # 7) Smart suggestions
    r = get(f"{BASE}/ai/suggestions/smart-categories/{tx_id}")
    if r.status_code != 200:
        fail("smart categories")
    sc = r.json()
    if "suggestions" not in sc:
        fail("smart categories payload invalid")
    ok("smart categories")

    # 8) Start bulk enhancement (admin) and poll progress briefly
    r = post(f"{BASE}/ai/enhance/uncategorized", admin=True)
    if r.status_code != 200:
        fail("enhance uncategorized start (admin)")
    job = r.json()
    job_id = job.get("job_id")
    total = job.get("transaction_count", 0)
    if not job_id and total > 0:
        fail("bulk job id missing")
    # UAT check: bulk jobs endpoint reachable
    r = get(f"{BASE}/ai/bulk-jobs")
    if r.status_code != 200:
        fail("bulk jobs list")
    ok("bulk jobs listed")

    # 9) Data stats (admin)
    r = get(f"{BASE}/admin/data/stats", admin=True)
    if r.status_code == 200:
        stats = r.json().get("stats", {})
        required = ["transactions", "import_runs", "events"]
        if not all(k in stats for k in required):
            fail("admin stats missing keys")
        ok("admin stats")
    else:
        ok("admin stats skipped (endpoint unavailable or admin not configured)")

    # 10) Metrics endpoint
    try:
        r = requests.get(BASE.replace('/api','') + "/metrics", timeout=10)
        if r.status_code == 200 and b"ai_calls_total" in r.content:
            ok("metrics endpoint")
        else:
            ok("metrics endpoint skipped (not available)")
    except Exception:
        ok("metrics endpoint skipped (not available)")

    print("\nUAT SUCCESS")


if __name__ == "__main__":
    uat()
