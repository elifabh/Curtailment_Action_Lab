#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python server.py "$@"
fi
if [[ -f .venv/Scripts/python.exe ]]; then
  exec .venv/Scripts/python.exe server.py "$@"
fi
if command -v py >/dev/null 2>&1; then
  exec py -3 server.py "$@"
fi
exec python3 server.py "$@"
