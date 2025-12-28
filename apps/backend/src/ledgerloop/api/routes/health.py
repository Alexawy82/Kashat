"""
Enhanced Health Check Endpoints.

Provides multiple health check endpoints for different use cases:
- /health - Basic health check (minimal overhead)
- /health/live - Kubernetes liveness probe
- /health/ready - Kubernetes readiness probe
- /health/detailed - Comprehensive component status
"""

from fastapi import APIRouter
from ...config import db_path, data_dir
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track server start time for uptime calculation
_start_time = time.time()


def _check_database() -> Dict[str, Any]:
    """Check database connectivity and basic stats."""
    try:
        from ...db import get_conn
        conn = get_conn()

        # Simple query to verify connectivity
        result = conn.execute("SELECT 1").fetchone()
        if result[0] != 1:
            return {"status": "unhealthy", "error": "Query verification failed"}

        # Get transaction count as a basic stat
        tx_count = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]

        # Get import run count
        import_count = conn.execute("SELECT COUNT(*) FROM import_run").fetchone()[0]

        # Check if tables exist (schema version check)
        tables = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """).fetchall()
        table_count = len(tables)

        return {
            "status": "healthy",
            "transaction_count": tx_count,
            "import_run_count": import_count,
            "table_count": table_count,
            "db_path": str(db_path())
        }
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def _check_filesystem() -> Dict[str, Any]:
    """Check filesystem access and data directory status."""
    try:
        data_directory = data_dir()

        # Check if data directory exists and is writable
        exists = data_directory.exists()
        is_writable = os.access(str(data_directory), os.W_OK) if exists else False

        # Check free disk space (approximate)
        try:
            stat = os.statvfs(str(data_directory))
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
            disk_usage_percent = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1) if stat.f_blocks > 0 else 0
        except (OSError, AttributeError):
            # Windows doesn't have statvfs
            free_gb = None
            total_gb = None
            disk_usage_percent = None

        status = "healthy" if exists and is_writable else "unhealthy"

        result = {
            "status": status,
            "data_dir": str(data_directory),
            "exists": exists,
            "writable": is_writable
        }

        if free_gb is not None:
            result["free_space_gb"] = round(free_gb, 2)
            result["total_space_gb"] = round(total_gb, 2)
            result["disk_usage_percent"] = disk_usage_percent

        return result
    except Exception as e:
        logger.warning(f"Filesystem health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def _check_ai_service() -> Dict[str, Any]:
    """Check AI service availability."""
    try:
        # Check if OpenAI API key is configured
        api_key = os.getenv("OPENAI_API_KEY", "")
        has_key = bool(api_key and len(api_key) > 10)

        return {
            "status": "healthy" if has_key else "degraded",
            "api_key_configured": has_key,
            "message": "AI features available" if has_key else "No API key - AI features disabled"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_auth_service() -> Dict[str, Any]:
    """Check authentication service status."""
    try:
        jwt_secret = os.getenv("LEDGERLOOP_JWT_SECRET", "")
        has_secret = bool(jwt_secret and len(jwt_secret) >= 32)

        # Check if we can import auth module
        try:
            from ..auth import decode_token
            auth_module_ok = True
        except ImportError:
            auth_module_ok = False

        return {
            "status": "healthy" if has_secret and auth_module_ok else "degraded",
            "jwt_secret_configured": has_secret,
            "auth_module_loaded": auth_module_ok
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _get_version() -> str:
    """Get application version."""
    try:
        # Try to get version from package or config
        return "1.0.0"  # Could be read from a version file
    except Exception:
        return "unknown"


def _get_uptime() -> Dict[str, Any]:
    """Get server uptime information."""
    uptime_seconds = time.time() - _start_time

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)

    return {
        "seconds": round(uptime_seconds, 2),
        "human": f"{days}d {hours}h {minutes}m {seconds}s",
        "started_at": datetime.fromtimestamp(_start_time).isoformat()
    }


@router.get("/health")
def health() -> dict:
    """
    Basic health check endpoint.

    Returns minimal information for quick health verification.
    Use /health/detailed for comprehensive status.
    """
    return {
        "status": "ok",
        "version": _get_version(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
def health_live() -> dict:
    """
    Kubernetes liveness probe endpoint.

    Indicates if the server process is running and responsive.
    Should return 200 if the application is alive (even if not fully ready).
    If this fails, Kubernetes should restart the container.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
def health_ready() -> dict:
    """
    Kubernetes readiness probe endpoint.

    Indicates if the server is ready to accept traffic.
    Checks critical dependencies (database, filesystem).
    If this fails, Kubernetes should stop sending traffic.
    """
    db_check = _check_database()
    fs_check = _check_filesystem()

    # Ready only if database and filesystem are healthy
    is_ready = (
        db_check.get("status") == "healthy" and
        fs_check.get("status") == "healthy"
    )

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": {
            "database": db_check.get("status"),
            "filesystem": fs_check.get("status")
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/detailed")
def health_detailed() -> dict:
    """
    Comprehensive health check with all component statuses.

    Provides detailed information about:
    - Server info (version, uptime)
    - Database connectivity and stats
    - Filesystem access
    - AI service availability
    - Authentication service status
    """
    # Run all checks
    db_check = _check_database()
    fs_check = _check_filesystem()
    ai_check = _check_ai_service()
    auth_check = _check_auth_service()
    uptime_info = _get_uptime()

    # Determine overall status
    statuses = [
        db_check.get("status"),
        fs_check.get("status"),
        auth_check.get("status")
    ]

    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "version": _get_version(),
        "environment": os.getenv("LEDGERLOOP_ENV", "development"),
        "uptime": uptime_info,
        "components": {
            "database": db_check,
            "filesystem": fs_check,
            "ai_service": ai_check,
            "auth_service": auth_check
        },
        "timestamp": datetime.utcnow().isoformat()
    }

