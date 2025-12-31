from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, Any

from .config import data_dir


CONFIG_FILE = data_dir() / "config.json"

def _default_lmstudio_base_url() -> str:
    # In Docker, 127.0.0.1 points at the container, not the host.
    # Prefer host.docker.internal (compose adds an extra_hosts mapping for Linux).
    try:
        if Path("/.dockerenv").exists() or os.getenv("KASHAT_IN_DOCKER") in ("1", "true", "yes"):
            return "http://host.docker.internal:1234/v1"
    except Exception:
        pass
    return "http://127.0.0.1:1234/v1"


DEFAULTS = {
    "recurring_tolerance": 0.15,
    "recurring_default_view": "all",
    "recurring_show_annual": True,
    "recurring_sparkline_period": 12,
    # Transactions page defaults
    "tx_default_sort_by": "posted_at",   # posted_at|amount|description|category|business|income|adjustment
    "tx_default_sort_dir": "desc",       # asc|desc
    "tx_include_transfers_default": False,
    "tx_business_filter_default": "",    # ""|"true"|"false"
    # AI configuration
    "ai_provider": "local",              # local|lmstudio|openai|auto
    "ai_openai_api_key": "",             # OpenAI API key (sensitive)
    "ai_openai_base_url": "",            # optional proxy/Azure base URL
    "ai_openai_model": "gpt-4o-mini",
    "ai_lmstudio_base_url": _default_lmstudio_base_url(),
    "ai_lmstudio_model": "",
    "ai_model_categorize": "",           # override per task
    "ai_model_merchant": "",
    "ai_model_anomaly": "",
    # AI timeouts/retries
    "ai_timeout": 30,
    "ai_connect_timeout": 5,
    "ai_max_retries": 2,
    "ai_retry_min_wait": 0.5,
    "ai_retry_max_wait": 10,
    "ai_retry_multiplier": 2,
    "ai_retry_jitter": True,
    "ai_max_concurrency": 2,
    "ai_temperature": 0.1,
    "ai_debug": False,
    # AI behavior
    "ai_auto_categorize_on_import": True,
    "ai_auto_categorize_min_conf": 0.7,
    "ai_auto_create_rules": True,
    "ai_auto_rule_min_conf": 0.7,
    "ai_anomaly_min_conf": 0.7,
    # AI processing queue controls
    "ai_processing_paused": False,
    "ai_batch_size": 20,
    "ai_batch_delay_ms": 500,
    "ai_max_concurrent_jobs": 2,
    "ai_job_timeout_minutes": 30,
    "ai_auto_start_on_import": True,
    # Dedup defaults
    "dedup_days_window": 30,
    "dedup_min_confidence": 0.7,
    # Dashboard
    "dashboard_default_period": "30d",
    "dashboard_show_ai": True,
    # Runtime controls
    "realtime_enabled": False,
    "sqlite_wal_mode": True,  # Use WAL mode for better concurrency
    "duckdb_threads": 0,
}


def load_settings() -> Dict[str, Any]:
    try:
        if CONFIG_FILE.exists():
            return {**DEFAULTS, **json.loads(CONFIG_FILE.read_text())}
    except Exception:
        pass
    return DEFAULTS.copy()


def save_settings(s: Dict[str, Any]) -> None:
    # persist only known keys
    data = {k: s.get(k, DEFAULTS[k]) for k in DEFAULTS}
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
