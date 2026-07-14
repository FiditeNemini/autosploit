#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ExploitBot"
BUNDLE_ID="ai.jangq.ExploitBot"
MIN_SYSTEM_VERSION="14.0"
VERSION="${EXPLOITBOT_RELEASE_VERSION:-1.0.0}"
IDENTITY="${EXPLOITBOT_SIGN_IDENTITY:-Developer ID Application: ShieldStack LLC (55KGF2S5AY)}"
NOTARY_PROFILE="${EXPLOITBOT_NOTARY_PROFILE:-}"
NOTARIZE_APPLE_ID="${NOTARIZE_APPLE_ID:-}"
NOTARIZE_TEAM_ID="${NOTARIZE_TEAM_ID:-}"
NOTARIZE_PASSWORD="${NOTARIZE_PASSWORD:-}"
DO_NOTARIZE=0

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/ExploitBot"
RELEASE_DIR="$ROOT_DIR/release"
APP_BUNDLE="$RELEASE_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
APP_BINARY="$APP_MACOS/$APP_NAME"
INFO_PLIST="$APP_CONTENTS/Info.plist"
DMG_PATH="$RELEASE_DIR/$APP_NAME.dmg"
MANIFEST_PATH="$RELEASE_DIR/release-manifest.json"
ENTITLEMENTS="$PACKAGE_DIR/ExploitBot.entitlements"
ENGINE_SOURCE_DIR="$ROOT_DIR/ExploitBotEngine"
ENGINE_BUNDLE_DIR="$APP_RESOURCES/ExploitBotEngine"
BUNDLED_PYTHON_SOURCE="${EXPLOITBOT_BUNDLED_PYTHON_SOURCE:-/Applications/vMLX.app/Contents/Resources/bundled-python}"
BUNDLED_PYTHON_DIR="$APP_RESOURCES/bundled-python"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --notarize)
      DO_NOTARIZE=1
      shift
      ;;
    --skip-notarize)
      DO_NOTARIZE=0
      shift
      ;;
    --identity)
      IDENTITY="${2:?missing identity}"
      shift 2
      ;;
    --notary-profile)
      NOTARY_PROFILE="${2:?missing notary profile}"
      shift 2
      ;;
    *)
      echo "usage: $0 [--skip-notarize|--notarize] [--identity NAME] [--notary-profile PROFILE]" >&2
      exit 2
      ;;
  esac
done

require_tool() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required tool: $1" >&2
    exit 1
  }
}

require_tool swift
require_tool codesign
require_tool hdiutil
require_tool xcrun
require_tool rsync
require_tool file

notary_args=()
if [[ -n "$NOTARY_PROFILE" ]]; then
  notary_args=(--keychain-profile "$NOTARY_PROFILE")
elif [[ -n "$NOTARIZE_APPLE_ID" && -n "$NOTARIZE_TEAM_ID" && -n "$NOTARIZE_PASSWORD" ]]; then
  notary_args=(--apple-id "$NOTARIZE_APPLE_ID" --team-id "$NOTARIZE_TEAM_ID" --password "$NOTARIZE_PASSWORD")
fi

if ! security find-identity -p codesigning -v | grep -F "$IDENTITY" >/dev/null; then
  echo "signing identity not found: $IDENTITY" >&2
  security find-identity -p codesigning -v >&2 || true
  exit 1
fi

rm -rf "$APP_BUNDLE" "$DMG_PATH" "$MANIFEST_PATH" "$RELEASE_DIR/dmg-root"
mkdir -p "$APP_MACOS" "$APP_RESOURCES" "$RELEASE_DIR/dmg-root"

swift build --package-path "$PACKAGE_DIR" -c release
BUILD_BINARY="$(swift build --package-path "$PACKAGE_DIR" -c release --show-bin-path)/$APP_NAME"

cp "$BUILD_BINARY" "$APP_BINARY"
chmod +x "$APP_BINARY"

if [[ -d "$PACKAGE_DIR/Resources" ]]; then
  rsync -a --delete "$PACKAGE_DIR/Resources/" "$APP_RESOURCES/"
fi

# Iter37 P0 (Codex F1 root fix v2): SPM's generated `Bundle.module`
# accessor is unusable for a macOS `.app`. It looks at `.app/root/*.bundle`
# (which codesign rejects), then falls back to a hard-coded
# `.build/...` path that only exists on the build machine. Rather
# than fight it, ChatService loads tab prompts from `Bundle.main`
# under `Contents/Resources/prompts/tabs/*.md` — the standard Apple
# location. This copy places the sources there.
PROMPT_SRC="$PACKAGE_DIR/Sources/ExploitBot/Resources/prompts"
if [[ ! -d "$PROMPT_SRC" ]]; then
  echo "FATAL: tab prompt source directory missing at $PROMPT_SRC" >&2
  echo "       (Contents/Resources/prompts/tabs/*.md is the load path via Bundle.main)" >&2
  exit 1
fi
rsync -a --delete "$PROMPT_SRC" "$APP_RESOURCES/"
# Clean up any prior-iteration copies of the SPM bundle that iter36
# put in Contents/Resources/ or iter37 attempt put at .app root
# (codesign rejected the root copy anyway).
rm -rf "$APP_RESOURCES/ExploitBot_ExploitBot.bundle"
rm -rf "$APP_BUNDLE/ExploitBot_ExploitBot.bundle"

if [[ -d "$ENGINE_SOURCE_DIR" ]]; then
  mkdir -p "$ENGINE_BUNDLE_DIR"
  rsync -a --delete \
    --exclude ".venv/" \
    --exclude ".pytest_cache/" \
    --exclude "__pycache__/" \
    --exclude "*/__pycache__/" \
    --exclude "testsuite/" \
    --exclude "*.egg-info/" \
    "$ENGINE_SOURCE_DIR/" "$ENGINE_BUNDLE_DIR/"
fi

if [[ ! -x "$BUNDLED_PYTHON_SOURCE/python/bin/python3" ]]; then
  echo "bundled Python runtime source is missing or not executable: $BUNDLED_PYTHON_SOURCE/python/bin/python3" >&2
  echo "set EXPLOITBOT_BUNDLED_PYTHON_SOURCE to a vMLX-compatible bundled-python directory" >&2
  exit 1
fi

mkdir -p "$BUNDLED_PYTHON_DIR"
rsync -a --delete \
  --exclude "__pycache__/" \
  --exclude "*/__pycache__/" \
  --exclude "*.pyc" \
  --exclude ".pytest_cache/" \
  --exclude "pip/cache/" \
  "$BUNDLED_PYTHON_SOURCE/" "$BUNDLED_PYTHON_DIR/"

cat >"$INFO_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>$VERSION</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>$MIN_SYSTEM_VERSION</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

if [[ -f "$APP_RESOURCES/AppIcon.icns" ]]; then
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string AppIcon" "$INFO_PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon" "$INFO_PLIST"
fi

while IFS= read -r -d '' nested_code; do
  if file "$nested_code" | grep -q "Mach-O"; then
    codesign --force \
      --timestamp \
      --options runtime \
      --sign "$IDENTITY" \
      "$nested_code"
  fi
done < <(find "$BUNDLED_PYTHON_DIR" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \) -print0)

codesign --force \
  --timestamp \
  --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$IDENTITY" \
  "$APP_BUNDLE"

codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"

NOTARIZATION_STATUS="not-submitted"
if [[ "$DO_NOTARIZE" == "1" ]]; then
  if [[ "${#notary_args[@]}" -eq 0 ]]; then
    echo "--notarize requires --notary-profile/EXPLOITBOT_NOTARY_PROFILE or NOTARIZE_APPLE_ID, NOTARIZE_TEAM_ID, and NOTARIZE_PASSWORD" >&2
    exit 1
  fi
  APP_ZIP="$RELEASE_DIR/$APP_NAME-app.zip"
  rm -f "$APP_ZIP"
  /usr/bin/ditto -c -k --keepParent "$APP_BUNDLE" "$APP_ZIP"
  xcrun notarytool submit "$APP_ZIP" "${notary_args[@]}" --wait
  xcrun stapler staple "$APP_BUNDLE"
  xcrun stapler validate "$APP_BUNDLE"
  rm -f "$APP_ZIP"
  NOTARIZATION_STATUS="app-submitted-and-stapled"
fi

cp -R "$APP_BUNDLE" "$RELEASE_DIR/dmg-root/"
ln -s /Applications "$RELEASE_DIR/dmg-root/Applications"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$RELEASE_DIR/dmg-root" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

codesign --force --timestamp --sign "$IDENTITY" "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"

if [[ "$DO_NOTARIZE" == "1" ]]; then
  xcrun notarytool submit "$DMG_PATH" "${notary_args[@]}" --wait
  xcrun stapler staple "$DMG_PATH"
  xcrun stapler validate "$DMG_PATH"
  NOTARIZATION_STATUS="submitted-and-stapled"
fi

TEAM_ID="$(codesign -dvvv "$APP_BUNDLE" 2>&1 | awk -F= '/TeamIdentifier=/{print $2; exit}')"
APP_BINARY_SHA="$(shasum -a 256 "$APP_BINARY" | awk '{print $1}')"
DMG_SHA="$(shasum -a 256 "$DMG_PATH" | awk '{print $1}')"
STARTER_CVES_DB_PRESENT="false"
APP_ICON_PRESENT="false"
PYTHON_ENGINE_PRESENT="false"
PYTHON_ENGINE_VENV_PRESENT="false"
BUNDLED_PYTHON_RUNTIME_PRESENT="false"
[[ -f "$APP_RESOURCES/starter-cves.db" ]] && STARTER_CVES_DB_PRESENT="true"
[[ -f "$APP_RESOURCES/AppIcon.icns" ]] && APP_ICON_PRESENT="true"
[[ -f "$ENGINE_BUNDLE_DIR/launch.py" && -f "$ENGINE_BUNDLE_DIR/vmlx_engine/server.py" ]] && PYTHON_ENGINE_PRESENT="true"
[[ -d "$ENGINE_BUNDLE_DIR/.venv" ]] && PYTHON_ENGINE_VENV_PRESENT="true"
[[ -x "$BUNDLED_PYTHON_DIR/python/bin/python3" && -d "$BUNDLED_PYTHON_DIR/python/lib" ]] && BUNDLED_PYTHON_RUNTIME_PRESENT="true"

APP_NAME="$APP_NAME" \
BUNDLE_ID="$BUNDLE_ID" \
VERSION="$VERSION" \
IDENTITY="$IDENTITY" \
TEAM_ID="$TEAM_ID" \
NOTARIZATION_STATUS="$NOTARIZATION_STATUS" \
APP_BINARY_SHA="$APP_BINARY_SHA" \
DMG_SHA="$DMG_SHA" \
STARTER_CVES_DB_PRESENT="$STARTER_CVES_DB_PRESENT" \
APP_ICON_PRESENT="$APP_ICON_PRESENT" \
PYTHON_ENGINE_PRESENT="$PYTHON_ENGINE_PRESENT" \
PYTHON_ENGINE_VENV_PRESENT="$PYTHON_ENGINE_VENV_PRESENT" \
BUNDLED_PYTHON_RUNTIME_PRESENT="$BUNDLED_PYTHON_RUNTIME_PRESENT" \
python3 - "$MANIFEST_PATH" <<'PY'
import json
import os
import sys

manifest = {
    "appName": os.environ["APP_NAME"],
    "bundleIdentifier": os.environ["BUNDLE_ID"],
    "version": os.environ["VERSION"],
    "identity": os.environ["IDENTITY"],
    "teamIdentifier": os.environ["TEAM_ID"],
    "hardenedRuntime": True,
    "notarizationStatus": os.environ["NOTARIZATION_STATUS"],
    "notarizationGate": "passed" if os.environ["NOTARIZATION_STATUS"] == "submitted-and-stapled" else "requires-notary-credentials",
    "notaryProfileRequired": False,
    "notarizationGateReason": "Notarization completed for the app and DMG." if os.environ["NOTARIZATION_STATUS"] == "submitted-and-stapled" else "Run with EXPLOITBOT_NOTARY_PROFILE or NOTARIZE_APPLE_ID/NOTARIZE_TEAM_ID/NOTARIZE_PASSWORD.",
    "artifacts": {
        "appPath": "release/ExploitBot.app",
        "dmgPath": "release/ExploitBot.dmg",
        "appBinarySha256": os.environ["APP_BINARY_SHA"],
        "dmgSha256": os.environ["DMG_SHA"],
    },
    "resources": {
        "starterCvesDb": os.environ["STARTER_CVES_DB_PRESENT"] == "true",
        "appIcon": os.environ["APP_ICON_PRESENT"] == "true",
        "pythonEngine": os.environ["PYTHON_ENGINE_PRESENT"] == "true",
        "pythonEngineVenv": os.environ["PYTHON_ENGINE_VENV_PRESENT"] == "true",
        "bundledPythonRuntime": os.environ["BUNDLED_PYTHON_RUNTIME_PRESENT"] == "true",
    },
    "commands": {
        "packageUnsigned": "./script/package_release.sh --skip-notarize",
        "notarizeWithProfile": "EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize",
        "notarizeWithEnv": "source /path/to/.env.signing && ./script/package_release.sh --notarize",
        "verifyAppSignature": "codesign --verify --deep --strict --verbose=2 release/ExploitBot.app",
        "verifyDmgSignature": "codesign --verify --verbose=2 release/ExploitBot.dmg",
        "validateStapledApp": "xcrun stapler validate release/ExploitBot.app",
        "validateStapledDmg": "xcrun stapler validate release/ExploitBot.dmg",
    },
}

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

echo "Release app: $APP_BUNDLE"
echo "Release dmg: $DMG_PATH"
echo "Release manifest: $MANIFEST_PATH"
