import os
from pathlib import Path


APP_NAME = "ledgerloop"


def _is_wsl() -> bool:
    """Detect if running under Windows Subsystem for Linux."""
    try:
        # Check /proc/version for WSL signature
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def _home_path_is_writable() -> bool:
    """Check if the default home-based data path is writable (not read-only OneDrive etc)."""
    try:
        home_data = Path.home() / f".{APP_NAME}"
        home_data.mkdir(parents=True, exist_ok=True)
        # Try to create a test file to verify write access
        test_file = home_data / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True
    except (PermissionError, OSError):
        return False


def _find_project_data_dir() -> Path:
    """Find the project root and use a data directory there."""
    # config.py is at apps/backend/src/ledgerloop/config.py
    # Walk up to find project root (where start script or apps/ exists)
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "apps").is_dir() or (parent / "start").exists():
            data_path = parent / "data"
            data_path.mkdir(parents=True, exist_ok=True)
            return data_path
    # Fallback to cwd/data
    return Path.cwd() / "data"


def data_dir() -> Path:
    env = os.getenv("LEDGERLOOP_DATA_DIR")
    if env:
        p = Path(env).expanduser().resolve()
    else:
        # In pytest, isolate to a repo-local data directory to avoid lock conflicts
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            p = Path.cwd() / ".pytestdata"
        # On WSL, check if home directory is writable; if not, use project data dir
        elif _is_wsl() and not _home_path_is_writable():
            p = _find_project_data_dir()
        else:
            p = Path.home() / f".{APP_NAME}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / f"{APP_NAME}.sqlite"


def tmp_dir() -> Path:
    p = data_dir() / "tmp"
    p.mkdir(parents=True, exist_ok=True)
    return p
