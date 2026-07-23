#!/usr/bin/env bash
# Minimal agent-friendly session bootstrap for sonycam.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/sonycam" ]]; then
  SONYCAM="$ROOT/.venv/bin/sonycam"
elif command -v sonycam >/dev/null 2>&1; then
  SONYCAM="$(command -v sonycam)"
else
  echo "sonycam not found. Run: make install" >&2
  exit 1
fi

"$SONYCAM" server start
"$SONYCAM" connect
"$SONYCAM" status --json
