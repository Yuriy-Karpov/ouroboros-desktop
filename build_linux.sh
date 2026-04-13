#!/bin/bash
set -e

VERSION=$(tr -d '[:space:]' < VERSION)
ARCHIVE_NAME="Ouroboros-${VERSION}-linux-$(uname -m).tar.gz"
MODE_FILE=".ouroboros-python-env"
if [ -n "${OUROBOROS_PYTHON_ENV_MODE:-}" ]; then
    PYTHON_ENV_MODE="$OUROBOROS_PYTHON_ENV_MODE"
elif [ -f "$MODE_FILE" ]; then
    PYTHON_ENV_MODE="$(tr -d '[:space:]' < "$MODE_FILE")"
else
    PYTHON_ENV_MODE="global"
fi
UV_BIN="${OUROBOROS_UV_BIN:-uv}"
BUILD_VENV="${BUILD_VENV:-.build-venv}"

PYTHON_CMD="${PYTHON_CMD:-python3}"
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
    PYTHON_CMD=python
fi

echo "=== Building Ouroboros for Linux (v${VERSION}) ==="

if [ ! -f "python-standalone/bin/python3" ]; then
    echo "ERROR: python-standalone/ not found."
    echo "Run first: bash scripts/download_python_standalone.sh"
    exit 1
fi

echo "--- Installing launcher dependencies ---"
if [ "$PYTHON_ENV_MODE" = "uv" ]; then
    "$UV_BIN" venv --allow-existing --python "$PYTHON_CMD" "$BUILD_VENV"
    "$UV_BIN" pip install --python "$BUILD_VENV/bin/python" -r requirements-launcher.txt
    BUILD_PYTHON="$BUILD_VENV/bin/python"
else
    "$PYTHON_CMD" -m pip install -q -r requirements-launcher.txt
    BUILD_PYTHON="$PYTHON_CMD"
fi

echo "--- Syncing agent dependencies ---"
if [ "$PYTHON_ENV_MODE" = "uv" ]; then
    "$UV_BIN" venv --allow-existing --python "python-standalone/bin/python3" ".venv"
    VIRTUAL_ENV="$PWD/.venv" PATH="$PWD/.venv/bin:$PATH" UV_PROJECT_ENVIRONMENT="$PWD/.venv" \
        "$UV_BIN" sync --active --extra browser
else
    python-standalone/bin/pip3 install -q -r requirements.txt
fi

rm -rf build dist

export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

echo "--- Running PyInstaller ---"
"$BUILD_PYTHON" -m PyInstaller Ouroboros.spec --clean --noconfirm

echo ""
echo "=== Creating archive ==="
cd dist
tar -czf "$ARCHIVE_NAME" Ouroboros/
cd ..

echo ""
echo "=== Done ==="
echo "Archive: dist/$ARCHIVE_NAME"
echo ""
echo "To run: extract and execute ./Ouroboros/Ouroboros"
