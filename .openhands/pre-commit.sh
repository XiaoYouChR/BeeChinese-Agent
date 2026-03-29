#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="${PYTHON_BIN:-python3}"
fi

"$PYTHON" -m compileall \
  "$ROOT_DIR/beechinese_agent" \
  "$ROOT_DIR/tools/run_beechinese_agent.py" \
  "$ROOT_DIR/main.py"

"$PYTHON" "$ROOT_DIR/tools/run_beechinese_agent.py" validate

echo "BeeChinese pre-commit checks passed."
