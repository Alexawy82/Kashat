#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/.pids"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"
BACKEND_HEALTH="${BACKEND_URL}/api/health"
FRONTEND_HEALTH="${FRONTEND_URL}/"

ensure_dirs() {
  mkdir -p "$LOG_DIR" "$PID_DIR"
}

prepare_log_file() {
  local log_path="$1"
  if [ -L "$log_path" ]; then
    local target
    target="$(readlink "$log_path")"
    local target_dir
    target_dir="$(dirname "$target")"
    if [ ! -d "$target_dir" ]; then
      rm -f "$log_path"
    fi
  fi
  if [ ! -e "$log_path" ]; then
    : > "$log_path"
  fi
}

detect_pkg_manager() {
  local web_dir="$ROOT_DIR/apps/web"
  if [ -f "$web_dir/pnpm-lock.yaml" ]; then
    echo "pnpm"
  elif [ -f "$web_dir/yarn.lock" ]; then
    echo "yarn"
  else
    echo "npm"
  fi
}

start_backend() {
  if [ -f "$PID_DIR/backend.pid" ] && kill -0 "$(cat "$PID_DIR/backend.pid")" 2>/dev/null; then
    echo "[dev-up] Backend already running (pid $(cat "$PID_DIR/backend.pid"))"
    return 0
  fi

  local uvicorn_cmd="$ROOT_DIR/.venv/bin/uvicorn"
  if [ ! -x "$uvicorn_cmd" ]; then
    uvicorn_cmd="uvicorn"
  fi

  echo "[dev-up] Starting backend..."
  (
    cd "$ROOT_DIR"
    export PYTHONPATH="$ROOT_DIR/apps/backend/src"
    nohup "$uvicorn_cmd" kashat.api.main:app --reload --host 127.0.0.1 --port 8000 \
      >"$BACKEND_LOG" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
  )
}

start_frontend() {
  if [ -f "$PID_DIR/frontend.pid" ] && kill -0 "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null; then
    echo "[dev-up] Frontend already running (pid $(cat "$PID_DIR/frontend.pid"))"
    return 0
  fi

  local pkg_mgr
  pkg_mgr="$(detect_pkg_manager)"
  local cmd=()
  case "$pkg_mgr" in
    pnpm) cmd=(pnpm dev -- --port 3000 --hostname 127.0.0.1) ;;
    yarn) cmd=(yarn dev -- --port 3000 --hostname 127.0.0.1) ;;
    *) cmd=(npm run dev -- --port 3000 --hostname 127.0.0.1) ;;
  esac

  echo "[dev-up] Starting frontend with $pkg_mgr..."
  (
    cd "$ROOT_DIR/apps/web"
    nohup "${cmd[@]}" >"$FRONTEND_LOG" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-45}"
  local delay="${4:-1}"

  for i in $(seq 1 "$attempts"); do
    local code
    code="$(curl -s --max-time 2 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")"
    if [ "$code" = "200" ]; then
      echo "[dev-up] $name ready ($url)"
      return 0
    fi
    sleep "$delay"
  done
  echo "[dev-up] $name not ready after ${attempts}s ($url)"
  return 1
}

health_only() {
  local ok=0
  wait_for_url "Backend" "$BACKEND_HEALTH" 5 1 || ok=1
  wait_for_url "Frontend" "$FRONTEND_HEALTH" 5 1 || ok=1
  return "$ok"
}

tail_logs() {
  echo "[dev-up] Tailing logs (ctrl-c to stop)..."
  tail -F "$BACKEND_LOG" "$FRONTEND_LOG" | awk '
    /^==> / {
      file=$2
      next
    }
    {
      label="log"
      if (file ~ /backend\.log$/) label="backend"
      if (file ~ /frontend\.log$/) label="frontend"
      if (tolower($0) ~ /(error|exception|traceback|eaddrinuse|err!)/) {
        print "[ERROR][" label "] " $0
      } else {
        print "[" label "] " $0
      }
      fflush()
    }'
}

mode="${1:-start}"
ensure_dirs
prepare_log_file "$BACKEND_LOG"
prepare_log_file "$FRONTEND_LOG"

case "$mode" in
  --health)
    health_only
    exit $?
    ;;
  --logs)
    tail_logs
    exit 0
    ;;
esac

start_backend
start_frontend

backend_ok=0
frontend_ok=0
wait_for_url "Backend" "$BACKEND_HEALTH" 45 1 || backend_ok=1
wait_for_url "Frontend" "$FRONTEND_HEALTH" 60 1 || frontend_ok=1

if [ "$backend_ok" -ne 0 ] || [ "$frontend_ok" -ne 0 ]; then
  echo "[dev-up] FAIL: services not ready."
  echo "[dev-up] Check logs: $BACKEND_LOG and $FRONTEND_LOG"
  "$ROOT_DIR/scripts/dev_down.sh" || true
  exit 1
fi

echo "[dev-up] PASS: backend + frontend ready."
echo "[dev-up] Open: $FRONTEND_URL"
tail_logs
