#!/bin/bash
set -euo pipefail

# Patch the .app bundle's launcher_bootstrap.py to match main-branch behavior:
# no destructive overwrite on version mismatch.

APP="${1:-/Users/anton/Desktop/Ouroboros.app}"
BUNDLE_FILE="$APP/Contents/Resources/ouroboros/launcher_bootstrap.py"
REPO_FILE="/Users/anton/Ouroboros/repo/ouroboros/launcher_bootstrap.py"

if [ ! -f "$BUNDLE_FILE" ]; then
    echo "ERROR: bundle file not found: $BUNDLE_FILE"
    exit 1
fi
if [ ! -f "$REPO_FILE" ]; then
    echo "ERROR: repo file not found: $REPO_FILE"
    exit 1
fi

echo "Patching bundle launcher_bootstrap.py..."
cp "$REPO_FILE" "$BUNDLE_FILE"
echo "Done. Bundle now matches repo."

echo ""
echo "Removing ad-hoc code signature (required after modifying bundle)..."
codesign --remove-signature "$APP" 2>/dev/null || true
echo "Re-signing with ad-hoc signature..."
codesign --force --deep --sign - "$APP"
echo "Done. You can now launch Ouroboros.app normally."
