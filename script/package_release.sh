#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ExploitBot"
BUNDLE_ID="ai.jangq.ExploitBot"
MIN_SYSTEM_VERSION="14.0"
VERSION="${EXPLOITBOT_RELEASE_VERSION:-0.1.0-beta}"
IDENTITY="${EXPLOITBOT_SIGN_IDENTITY:-Developer ID Application: ShieldStack LLC (55KGF2S5AY)}"
NOTARY_PROFILE="${EXPLOITBOT_NOTARY_PROFILE:-}"
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
DMG_PATH="$RELEASE_DIR/$APP_NAME-beta.dmg"
ENTITLEMENTS="$PACKAGE_DIR/ExploitBot.entitlements"

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

if ! security find-identity -p codesigning -v | grep -F "$IDENTITY" >/dev/null; then
  echo "signing identity not found: $IDENTITY" >&2
  security find-identity -p codesigning -v >&2 || true
  exit 1
fi

rm -rf "$APP_BUNDLE" "$DMG_PATH" "$RELEASE_DIR/dmg-root"
mkdir -p "$APP_MACOS" "$APP_RESOURCES" "$RELEASE_DIR/dmg-root"

swift build --package-path "$PACKAGE_DIR" -c release
BUILD_BINARY="$(swift build --package-path "$PACKAGE_DIR" -c release --show-bin-path)/$APP_NAME"

cp "$BUILD_BINARY" "$APP_BINARY"
chmod +x "$APP_BINARY"

if [[ -d "$PACKAGE_DIR/Resources" ]]; then
  rsync -a --delete "$PACKAGE_DIR/Resources/" "$APP_RESOURCES/"
fi

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

codesign --force \
  --timestamp \
  --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$IDENTITY" \
  "$APP_BUNDLE"

codesign --verify --deep --strict --verbose=2 "$APP_BUNDLE"

cp -R "$APP_BUNDLE" "$RELEASE_DIR/dmg-root/"
ln -s /Applications "$RELEASE_DIR/dmg-root/Applications"
hdiutil create \
  -volname "$APP_NAME Beta" \
  -srcfolder "$RELEASE_DIR/dmg-root" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

codesign --force --timestamp --sign "$IDENTITY" "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"

if [[ "$DO_NOTARIZE" == "1" ]]; then
  if [[ -z "$NOTARY_PROFILE" ]]; then
    echo "--notarize requires --notary-profile or EXPLOITBOT_NOTARY_PROFILE" >&2
    exit 1
  fi
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
fi

echo "Release app: $APP_BUNDLE"
echo "Release dmg: $DMG_PATH"
