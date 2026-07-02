#!/usr/bin/env bash
# postCreate: provision the mystmd-pythonapi toolchain.
#   - Node/npm come from the Dockerfile.
#   - python + uv come from the base image.
#   - The Python venv lives in the shared /cache volume ($UV_PROJECT_ENVIRONMENT),
#     so it survives rebuilds and is keyed by workspace path.
#

set -euo pipefail
cd "$(dirname "$0")/.."

# --- Python (uv from the base image -> venv in the shared cache) ---
# uv sync builds the venv at $UV_PROJECT_ENVIRONMENT from pyproject.toml/uv.lock.
# Use the base image's Python 3.14; never download a managed interpreter.
uv sync --all-extras --python 3.14 --python-preference only-system

# --- Node deps (node/npm come from the Dockerfile) ---
npm ci

echo "toolchain ready — run the acceptance oracle with: ./run_all.sh"
