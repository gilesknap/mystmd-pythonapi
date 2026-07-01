#!/usr/bin/env bash
# postCreate: provision the mystmd-pythonapi toolchain (Node + Python).
#
# Idempotent and defensive: it always installs the toolchain, but guards the
# project-specific steps (npm ci, the oracle) behind file checks so it no-ops
# cleanly on branches that don't yet carry the code (e.g. today's `main`, which
# has only SPEC.md). Once the implementation branch lands, the same script
# builds a fully working environment with no changes.
#
# Claude is NOT installed here. Guest it in yourself by running `./install`
# from a peer clone at /workspaces/claude-sandbox — this devcontainer already
# passes the one thing it needs (runArgs --device=/dev/net/tun).
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Python (uv -> ./.venv, exactly where run_all.sh looks) ---
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv python install 3.12
uv venv --python 3.12 .venv
if [ -f requirements.txt ]; then
    uv pip install --python .venv/bin/python -r requirements.txt
else
    # No Python manifest in the repo yet; pin the SPEC.md M0 deps here.
    uv pip install --python .venv/bin/python griffe sphinx sphobjinv numpydoc pytest
fi

# --- Node deps (node/npm come from the devcontainer feature) ---
if [ -f package.json ]; then
    npm ci
fi

if [ -f run_all.sh ]; then
    echo "toolchain ready — run the acceptance oracle with: ./run_all.sh"
else
    echo "toolchain ready — project code is not on this branch yet (only SPEC.md)."
fi
