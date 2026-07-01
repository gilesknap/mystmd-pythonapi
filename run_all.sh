#!/usr/bin/env bash
# Acceptance oracle (SPEC §9). Its exit code is the loop's only truth.
# Usage: ./run_all.sh [-x]   (-x = stop at first failing test)
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/root/.local/bin:$PATH"
VENV_PY="$PWD/.venv/bin/python"

PYTEST_ARGS=(-q)
if [ "${1:-}" = "-x" ]; then PYTEST_ARGS=(-q -x); fi

echo "== [1/3] build plugin (dist/*.mjs) =="
npm run build

echo "== [2/3] generate build/objects.inv from the stub extractor =="
node dist/cli.mjs

echo "== [3/3] run acceptance tests (T1-T8) =="
"$VENV_PY" -m pytest tests/ "${PYTEST_ARGS[@]}"
