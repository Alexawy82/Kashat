import os
import logging
import time
from typing import Dict, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse, Response

from ..db import connect, close
from ..logging_config import setup_logging
from ..metrics import (
    generate_latest, 
    CONTENT_TYPE_LATEST,
    record_request_metrics,
    update_database_metrics,
    get_metrics_snapshot
)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiting
from slowapi.errors import RateLimitExceeded
from .limiter import limiter

# CORS helpers
def _get_cors_origins() -> list[str]:
    raw = (os.getenv("KASHAT_CORS") or "").strip()
    if raw == "" or raw.lower() == "localhost":
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    if raw == "*":
        return ["*"]
    return [v.strip() for v in raw.split(",") if v.strip()]


def _allow_cors_credentials() -> bool:
    origins = _get_cors_origins()
    return "*" not in origins

# --- Metrics Middleware ---
# Kept for observability, but simplified.

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        method = request.method
        route = request.url.path # Simplified route tracking
        
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            logger.error(f"Request failed: {method} {route} - {e}")
            raise e

        elapsed = time.perf_counter() - start
        status = response.status_code

        # Log slow requests (>500ms)
        duration_ms = int(elapsed * 1000)
        if duration_ms > 500:
             logger.warning(f"SLOW REQUEST: {method} {route} -> {status} ({duration_ms}ms)")
        
        return response

# --- App Factory ---

def create_app() -> FastAPI:
    
    # Lifespan context for DB connection
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if os.getenv("PYTEST_CURRENT_TEST") is None:
            connect()
            logger.info("Database connected.")
        yield
        if os.getenv("PYTEST_CURRENT_TEST") is None:
            close()
            logger.info("Database disconnected.")

    app = FastAPI(
        title="Kashat API",
        version="2.0.0", # Bumped for the overhaul
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None # Disable redoc to save resources
    )

    # 1. CORS - allowlist by default, override via KASHAT_CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=_allow_cors_credentials(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Metrics
    app.add_middleware(MetricsMiddleware)

    # 3. Rate Limiting
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"}
        )

    # 4. Global Error Handling
    from .errors import register_exception_handlers
    register_exception_handlers(app)

    # --- Routes ---
    
    # Core
    from .routes.health import router as health_router
    from .routes.transactions import router as tx_router
    from .routes.categories import router as cat_router
    from .routes.rules import router as rules_router
    from .routes.accounts import router as accounts_router
    from .routes.settings import router as settings_router
    
    # Intelligence / Features
    from .routes.imports import router as import_router
    from .routes.transfers import router as transfers_router
    from .routes.recurring import router as recurring_router
    from .routes.analytics import router as analytics_router
    from .routes.export import router as export_router
    from .routes.audit import router as audit_router
    from .routes.detect import router as detect_router
    from .routes.p2p import router as p2p_router
    from .routes.workflows import router as workflows_router
    
    # AI - Consolidated
    from .routes.ai import router as ai_router
    from .routes.ai_categories import router as ai_categories_router
    from .routes.ai_enhanced import router as ai_enhanced_router
    from .routes.intelligence import router as intelligence_router
    from .routes.ai_workflow import router as ai_workflow_router

    # New Features (Phase 5)
    from .routes.networth import router as networth_router
    from .routes.calendar import router as calendar_router
    from .routes.insights import router as insights_router
    from .routes.budgets import router as budgets_router

    # Admin
    from .routes.admin import router as admin_router

    # Register
    app.include_router(health_router, prefix="/api")
    app.include_router(tx_router, prefix="/api")
    app.include_router(accounts_router, prefix="/api")
    app.include_router(cat_router, prefix="/api")
    app.include_router(rules_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    
    app.include_router(import_router, prefix="/api")
    app.include_router(transfers_router, prefix="/api")
    app.include_router(recurring_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(detect_router, prefix="/api")
    app.include_router(p2p_router, prefix="/api")
    app.include_router(workflows_router, prefix="/api")
    
    app.include_router(ai_router, prefix="/api")
    app.include_router(ai_categories_router, prefix="/api")
    app.include_router(ai_enhanced_router, prefix="/api")
    app.include_router(intelligence_router, prefix="/api")
    app.include_router(ai_workflow_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    # New Features (Phase 5)
    app.include_router(networth_router, prefix="/api")
    app.include_router(calendar_router, prefix="/api")
    app.include_router(insights_router, prefix="/api")
    app.include_router(budgets_router, prefix="/api")

    # --- Metrics Endpoint ---
    if os.getenv("KASHAT_EXPOSE_METRICS", "false").lower() in ("1", "true", "yes"):
        @app.get("/metrics")
        def metrics():
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app

# Create app instance for uvicorn
app = create_app()
