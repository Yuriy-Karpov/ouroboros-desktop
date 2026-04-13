#!/bin/bash
set -euo pipefail

MODE_FILE=".ouroboros-python-env"
UV_BIN="${OUROBOROS_UV_BIN:-uv}"
PYTHON_CMD="${PYTHON_CMD:-python3}"

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
    PYTHON_CMD=python
fi

MODE="${1:-}"
if [ -z "$MODE" ]; then
    echo "Usage: bash scripts/setup_python_env.sh <uv|global>" >&2
    echo "This is an internal helper. Use bash scripts/install.sh for interactive installation." >&2
    exit 1
fi

case "$MODE" in
    uv|UV|venv|uv-venv) MODE="uv" ;;
    global|GLOBAL|pip) MODE="global" ;;
    *)
        echo "Unknown mode: ${MODE}" >&2
        exit 1
        ;;
esac

printf '%s\n' "$MODE" > "$MODE_FILE"
echo "Saved mode to $MODE_FILE: $MODE"

if [ "$MODE" = "uv" ]; then
    "$UV_BIN" venv --allow-existing --python "$PYTHON_CMD" .venv
    VIRTUAL_ENV="$PWD/.venv" PATH="$PWD/.venv/bin:$PATH" UV_PROJECT_ENVIRONMENT="$PWD/.venv" \
        "$UV_BIN" sync --active --extra browser
else
    "$PYTHON_CMD" -m pip install -r requirements.txt
fi

echo "Python environment is ready in mode: $MODE"
