from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...settings import load_settings, save_settings


router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsBody(BaseModel):
    recurring_tolerance: float | None = None
    tx_default_sort_by: str | None = None
    tx_default_sort_dir: str | None = None
    tx_include_transfers_default: bool | None = None
    tx_business_filter_default: str | None = None
    # AI
    ai_provider: str | None = None
    ai_openai_api_key: str | None = None
    ai_openai_base_url: str | None = None
    ai_lmstudio_base_url: str | None = None
    ai_model_categorize: str | None = None
    ai_model_merchant: str | None = None
    ai_model_anomaly: str | None = None
    # AI behavior
    ai_auto_categorize_on_import: bool | None = None
    ai_auto_categorize_min_conf: float | None = None
    ai_auto_create_rules: bool | None = None
    ai_auto_rule_min_conf: float | None = None
    ai_anomaly_min_conf: float | None = None
    # Dashboard
    dashboard_default_period: str | None = None  # e.g., '30d','90d','365d'
    dashboard_show_ai: bool | None = None
    # Runtime
    realtime_enabled: bool | None = None
    duckdb_threads: int | None = None


@router.get("")
def get_settings():
    return load_settings()


@router.post("")
def set_settings(body: SettingsBody):
    s = load_settings()
    if body.recurring_tolerance is not None:
        s["recurring_tolerance"] = float(body.recurring_tolerance)
    if body.tx_default_sort_by is not None:
        s["tx_default_sort_by"] = str(body.tx_default_sort_by)
    if body.tx_default_sort_dir is not None:
        s["tx_default_sort_dir"] = str(body.tx_default_sort_dir)
    if body.tx_include_transfers_default is not None:
        s["tx_include_transfers_default"] = bool(body.tx_include_transfers_default)
    if body.tx_business_filter_default is not None:
        s["tx_business_filter_default"] = str(body.tx_business_filter_default)
    # AI
    if body.ai_provider is not None:
        s["ai_provider"] = str(body.ai_provider)
    if body.ai_openai_api_key is not None:
        s["ai_openai_api_key"] = str(body.ai_openai_api_key)
    if body.ai_openai_base_url is not None:
        s["ai_openai_base_url"] = str(body.ai_openai_base_url)
    if body.ai_lmstudio_base_url is not None:
        s["ai_lmstudio_base_url"] = str(body.ai_lmstudio_base_url)
    if body.ai_model_categorize is not None:
        s["ai_model_categorize"] = str(body.ai_model_categorize)
    if body.ai_model_merchant is not None:
        s["ai_model_merchant"] = str(body.ai_model_merchant)
    if body.ai_model_anomaly is not None:
        s["ai_model_anomaly"] = str(body.ai_model_anomaly)
    # AI behavior
    if body.ai_auto_categorize_on_import is not None:
        s["ai_auto_categorize_on_import"] = bool(body.ai_auto_categorize_on_import)
    if body.ai_auto_categorize_min_conf is not None:
        s["ai_auto_categorize_min_conf"] = float(body.ai_auto_categorize_min_conf)
    if body.ai_auto_create_rules is not None:
        s["ai_auto_create_rules"] = bool(body.ai_auto_create_rules)
    if body.ai_auto_rule_min_conf is not None:
        s["ai_auto_rule_min_conf"] = float(body.ai_auto_rule_min_conf)
    if body.ai_anomaly_min_conf is not None:
        s["ai_anomaly_min_conf"] = float(body.ai_anomaly_min_conf)
    # Dashboard
    if body.dashboard_default_period is not None:
        s["dashboard_default_period"] = str(body.dashboard_default_period)
    if body.dashboard_show_ai is not None:
        s["dashboard_show_ai"] = bool(body.dashboard_show_ai)
    # Runtime
    if body.realtime_enabled is not None:
        s["realtime_enabled"] = bool(body.realtime_enabled)
    if body.duckdb_threads is not None:
        try:
            s["duckdb_threads"] = max(0, int(body.duckdb_threads))
        except Exception:
            pass
    save_settings(s)
    return s


class AISettingsBody(BaseModel):
    """Dedicated AI settings update"""
    ai_provider: str | None = None  # "auto", "lmstudio", "openai", "local"
    ai_auto_categorize_on_import: bool | None = None
    ai_auto_categorize_min_conf: float | None = None
    ai_debug: bool | None = None


@router.get("/ai")
def get_ai_settings():
    """Get AI-specific settings"""
    import os
    s = load_settings()
    return {
        "ai_provider": s.get("ai_provider", "auto"),
        "ai_lmstudio_base_url": s.get("ai_lmstudio_base_url", "http://127.0.0.1:1234/v1"),
        "ai_openai_base_url": s.get("ai_openai_base_url", ""),
        "ai_auto_categorize_on_import": s.get("ai_auto_categorize_on_import", True),
        "ai_auto_categorize_min_conf": s.get("ai_auto_categorize_min_conf", 0.7),
        "ai_model_categorize": s.get("ai_model_categorize", ""),
        "ai_debug": os.getenv("LEDGERLOOP_AI_DEBUG", "false").lower() == "true",
    }


@router.put("/ai")
def update_ai_settings(body: AISettingsBody):
    """Update AI-specific settings at runtime"""
    import os
    s = load_settings()

    if body.ai_provider is not None:
        s["ai_provider"] = str(body.ai_provider)
    if body.ai_auto_categorize_on_import is not None:
        s["ai_auto_categorize_on_import"] = bool(body.ai_auto_categorize_on_import)
    if body.ai_auto_categorize_min_conf is not None:
        s["ai_auto_categorize_min_conf"] = float(body.ai_auto_categorize_min_conf)
    if body.ai_debug is not None:
        # Set environment variable for debug mode
        os.environ["LEDGERLOOP_AI_DEBUG"] = "true" if body.ai_debug else "false"

    save_settings(s)

    # Reset AI service to pick up new settings
    from ...ai import reset_ai_service
    reset_ai_service()

    return {
        "status": "updated",
        "settings": get_ai_settings()
    }
