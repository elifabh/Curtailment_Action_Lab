#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if command -v py >/dev/null 2>&1; then
  py -3 -m venv .venv
else
  python3 -m venv .venv
fi
if [[ -f .venv/Scripts/python.exe ]]; then
  .venv/Scripts/python.exe -m pip install -r requirements.txt
else
  .venv/bin/python -m pip install -r requirements.txt
fi
printf '\nInstallation complete. Run: bash START_LOCAL.sh\n'
