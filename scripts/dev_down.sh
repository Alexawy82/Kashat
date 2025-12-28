#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT_DIR/.pids"

stop_pid() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [ ! -f "$pid_file" ]; then
    echo "[dev-down] No PID file for $name"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "[dev-down] Stopping $name (pid $pid)..."
    kill "$pid" || true
    for _ in $(seq 1 10); do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "[dev-down] $name did not stop; sending SIGKILL"
      kill -9 "$pid" || true
    fi
  else
    echo "[dev-down] $name not running (stale pid $pid)"
  fi
  rm -f "$pid_file"
}

stop_pid "backend"
stop_pid "frontend"
