#!/bin/bash
set -e

SIGN_IDENTITY="Developer ID Application: Ian Mironov (WHY6PAKA5V)"
NOTARYTOOL_PROFILE="ouroboros-notarize"
ENTITLEMENTS="entitlements.plist"
SIGN_MODE="${OUROBOROS_SIGN:-1}"
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

APP_PATH="dist/Ouroboros.app"
DMG_NAME="Ouroboros-$(cat VERSION | tr -d '[:space:]').dmg"
DMG_PATH="dist/$DMG_NAME"

echo "=== Building Ouroboros.app ==="

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

echo "--- Normalizing python-standalone symlinks for PyInstaller ---"
"$BUILD_PYTHON" - <<'PY'
import pathlib
import shutil

root = pathlib.Path("python-standalone")
replaced = 0

for path in sorted(root.rglob("*")):
    if not path.is_symlink():
        continue
    target = path.resolve()
    path.unlink()
    if target.is_dir():
        shutil.copytree(target, path)
    else:
        shutil.copy2(target, path)
    replaced += 1

print(f"Replaced {replaced} symlinks in python-standalone")
PY

rm -rf build dist

echo "--- Running PyInstaller ---"
"$BUILD_PYTHON" -m PyInstaller Ouroboros.spec --clean --noconfirm

if [ "$SIGN_MODE" != "0" ]; then
    echo ""
    echo "=== Signing Ouroboros.app ==="

    echo "--- Finding and signing all Mach-O binaries ---"
    find "$APP_PATH" -type f | while read -r f; do
        if file "$f" | grep -q "Mach-O"; then
            codesign -s "$SIGN_IDENTITY" --timestamp --force --options runtime \
                --entitlements "$ENTITLEMENTS" "$f" 2>&1 || true
        fi
    done
    echo "Signed embedded binaries"

    echo "--- Signing the app bundle ---"
    codesign -s "$SIGN_IDENTITY" --timestamp --force --options runtime \
        --entitlements "$ENTITLEMENTS" "$APP_PATH"

    echo "--- Verifying signature ---"
    codesign -dvv "$APP_PATH"
    codesign --verify --strict "$APP_PATH"
    echo "Signature OK"
else
    echo ""
    echo "=== Skipping signing (OUROBOROS_SIGN=0) ==="
fi

echo ""
echo "=== Creating DMG ==="
hdiutil create -volname Ouroboros -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

if [ "$SIGN_MODE" != "0" ]; then
    codesign -s "$SIGN_IDENTITY" --timestamp "$DMG_PATH"
fi

echo ""
echo "=== Done ==="
if [ "$SIGN_MODE" != "0" ]; then
    echo "Signed app: $APP_PATH"
    echo "Signed DMG: $DMG_PATH"
else
    echo "Unsigned app: $APP_PATH"
    echo "Unsigned DMG: $DMG_PATH"
fi
echo "(Not notarized — users need right-click → Open on first launch)"
