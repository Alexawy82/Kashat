#!/usr/bin/env bash
set -euo pipefail

# Validate that archived components aren't imported by active code.
# Adjust patterns below if additional archived modules are added.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

PATTERNS=(
  "src/components/mobile/"
  "src/components/help/"
)

FAIL=0
for pat in "${PATTERNS[@]}"; do
  # Grep for imports referencing these paths, excluding the files themselves
  if rg -n "from '.*${pat}.*'|from \".*${pat}.*\"|import .*${pat}" apps/web/src --no-ignore -S | rg -v "${pat}.*\.tsx"; then
    echo "Found imports referencing archived pattern: ${pat}" >&2
    FAIL=1
  fi
done

if [[ $FAIL -ne 0 ]]; then
  echo "Archived component imports detected. Please remove or replace these imports." >&2
  exit 1
else
  echo "No archived component imports detected."
fi

