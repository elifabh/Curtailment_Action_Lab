#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python -m pip install -r requirements-irish-extension.txt
elif [[ -f .venv/Scripts/python.exe ]]; then
  .venv/Scripts/python.exe -m pip install -r requirements-irish-extension.txt
elif command -v py >/dev/null 2>&1; then
  py -3 -m pip install -r requirements-irish-extension.txt
else
  python3 -m pip install -r requirements-irish-extension.txt
fi
printf '%s\n' 'Installation complete. Restart START_LOCAL.sh.'
