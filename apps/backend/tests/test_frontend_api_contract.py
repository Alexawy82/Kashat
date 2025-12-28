from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FoundEndpoint:
    path: str
    file: str


def _strip_query(path: str) -> str:
    return path.split("?", 1)[0]


_PLACEHOLDER_RE = re.compile(r"\{[^/{}]+\}")


def _is_placeholder(seg: str) -> bool:
    return bool(_PLACEHOLDER_RE.fullmatch(seg))


def _segments(path: str) -> list[str]:
    return [s for s in path.strip("/").split("/") if s]


def _compatible(front: str, back: str) -> bool:
    fs = _segments(front)
    bs = _segments(back)
    if len(fs) != len(bs):
        return False
    for f, b in zip(fs, bs, strict=True):
        if f == b:
            continue
        if _is_placeholder(f) or _is_placeholder(b):
            continue
        return False
    return True


def _extract_from_template(template: str) -> str | None:
    # Replace ${...} with a placeholder segment marker.
    t = re.sub(r"\$\{[^}]*\}", "{param}", template)
    # If this template was truncated (e.g. nested template literals), drop any incomplete ${... part.
    if "${" in t and "}" not in t:
        t = t.split("${", 1)[0]
    # Grab the first path-like segment.
    m = re.search(r"/[^`\s\"']+", t)
    if not m:
        return None
    path = _strip_query(m.group(0))
    # Ignore obviously non-path constructs.
    if "/../" in path:
        return None
    return path


def _extract_call_endpoints(text: str, func_name: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"\b{re.escape(func_name)}\s*\(", text):
        window = text[m.end() : m.end() + 500]

        # Single-quoted: '/...'
        for s in re.findall(r"'(/[^']+)'", window):
            found.append(_strip_query(s))
        # Double-quoted: "/..."
        for s in re.findall(r'"(/[^"]+)"', window):
            found.append(_strip_query(s))
        # Template literal: `...`
        for s in re.findall(r"`([^`]+)`", window):
            p = _extract_from_template(s)
            if p:
                found.append(p)
    return found


def _normalize_frontend_path(path: str) -> str | None:
    if path == "/api":
        return None
    # Allow direct metrics scrape.
    if path == "/metrics":
        return path
    if path.startswith("/api/"):
        return path
    if not path.startswith("/"):
        return None
    return "/api" + path


def _frontend_sources() -> list[Path]:
    ignore_names = {
        # Not wired into the running app; contains example/external service endpoints.
        "FeatureFlag.ts",
    }
    roots = [
        Path("apps/web/src/app"),
        Path("apps/web/src/components"),
        Path("apps/web/src/services"),
        Path("apps/web/src/hooks"),
        Path("apps/web/src/utils"),
    ]
    out: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        out.extend([p for p in r.rglob("*.ts*") if p.is_file() and p.name not in ignore_names])
    return out


def _backend_routes() -> set[str]:
    from kashat.api import create_app

    app = create_app()
    out: set[str] = set()
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            continue
        out.add(path)
    return out


def test_frontend_api_contract_surface() -> None:
    backend = _backend_routes()

    # Realtime is intentionally optional: backend only includes it when LEDGERLOOP_INCLUDE_REALTIME_ROUTES=true.
    optional_prefixes = (
        "/api/realtime/",
        "/api/realtime",  # tolerate exact prefix
    )

    found: list[FoundEndpoint] = []
    for p in _frontend_sources():
        text = p.read_text(errors="ignore")
        candidates = []
        candidates.extend(_extract_call_endpoints(text, "apiRequest"))
        candidates.extend(_extract_call_endpoints(text, "fetch"))

        for raw in candidates:
            norm = _normalize_frontend_path(raw)
            if not norm:
                continue
            # Skip non-API page routes that happen to start with '/api' in string literals.
            # (e.g. '/api' as a base constant).
            if norm == "/api":
                continue
            found.append(FoundEndpoint(path=norm, file=str(p)))

    missing: dict[str, set[str]] = {}
    for fe in found:
        if fe.path.startswith(optional_prefixes):
            continue

        ok = any(_compatible(fe.path, be) for be in backend)
        if not ok:
            missing.setdefault(fe.path, set()).add(fe.file)

    if missing:
        details = "\n".join(
            f"- {path} (found in: {', '.join(sorted(files))})"
            for path, files in sorted(missing.items())
        )
        raise AssertionError(f"Frontend references unknown backend routes:\n{details}")
