#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="${PYTHON_BIN:-python3}"

mkdir -p \
  "$ROOT_DIR/.openhands" \
  "$ROOT_DIR/.agents/agents" \
  "$ROOT_DIR/.agents/skills" \
  "$ROOT_DIR/docs" \
  "$ROOT_DIR/tools" \
  "$ROOT_DIR/beechinese_agent"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  "$DEFAULT_PYTHON" -m venv "$ROOT_DIR/.venv"
  PYTHON="$ROOT_DIR/.venv/bin/python"
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$ROOT_DIR/requirements.txt"

echo "BeeChinese OpenHands setup complete."
echo "Python: $PYTHON"
echo "Next step: $PYTHON $ROOT_DIR/tools/run_beechinese_agent.py validate"
