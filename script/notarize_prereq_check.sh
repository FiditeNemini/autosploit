#!/usr/bin/env bash
set -euo pipefail

# Verify that everything needed for `./script/package_release.sh --notarize`
# is in place BEFORE spending a long build cycle just to fail at the notarize
# step. Read-only — makes no changes.

IDENTITY="${EXPLOITBOT_SIGN_IDENTITY:-Developer ID Application: ShieldStack LLC (55KGF2S5AY)}"
NOTARY_PROFILE="${EXPLOITBOT_NOTARY_PROFILE:-}"
NOTARIZE_APPLE_ID="${NOTARIZE_APPLE_ID:-}"
NOTARIZE_TEAM_ID="${NOTARIZE_TEAM_ID:-}"
NOTARIZE_PASSWORD="${NOTARIZE_PASSWORD:-}"
BUNDLED_PYTHON_SOURCE="${EXPLOITBOT_BUNDLED_PYTHON_SOURCE:-/Applications/vMLX.app/Contents/Resources/bundled-python}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/ExploitBot"

pass=0
fail=0

ok() { echo "  ✓ $1"; pass=$((pass+1)); }
bad() { echo "  ✗ $1"; fail=$((fail+1)); }

echo "== toolchain =="
for tool in swift codesign hdiutil xcrun rsync file security shasum; do
  command -v "$tool" >/dev/null 2>&1 && ok "$tool" || bad "$tool missing"
done

echo ""
echo "== signing identity =="
if security find-identity -p codesigning -v | grep -F "$IDENTITY" >/dev/null; then
  ok "signing identity present: $IDENTITY"
else
  bad "signing identity missing: $IDENTITY"
  security find-identity -p codesigning -v || true
fi

echo ""
echo "== bundle inputs =="
[[ -x "$BUNDLED_PYTHON_SOURCE/python/bin/python3" ]] && ok "bundled-python source" || bad "bundled-python source ($BUNDLED_PYTHON_SOURCE/python/bin/python3)"
[[ -f "$PACKAGE_DIR/ExploitBot.entitlements" ]] && ok "entitlements" || bad "entitlements ($PACKAGE_DIR/ExploitBot.entitlements)"
[[ -f "$PACKAGE_DIR/Resources/AppIcon.icns" ]] && ok "AppIcon.icns" || bad "AppIcon.icns"
[[ -f "$PACKAGE_DIR/Resources/starter-cves.db" ]] && ok "starter-cves.db" || bad "starter-cves.db"
[[ -f "$ROOT_DIR/ExploitBotEngine/launch.py" ]] && ok "engine launch.py" || bad "engine launch.py"

echo ""
echo "== notary credentials =="
if [[ -n "$NOTARY_PROFILE" ]]; then
  ok "EXPLOITBOT_NOTARY_PROFILE set: $NOTARY_PROFILE"
  # Try to read the profile without doing a real submission.
  if xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null 2>&1; then
    ok "notary profile reachable (history call succeeded)"
  else
    bad "notary profile FAILED — check keychain access + credential validity"
  fi
elif [[ -n "$NOTARIZE_APPLE_ID" && -n "$NOTARIZE_TEAM_ID" && -n "$NOTARIZE_PASSWORD" ]]; then
  ok "NOTARIZE_APPLE_ID + TEAM_ID + PASSWORD all set"
  if xcrun notarytool history \
      --apple-id "$NOTARIZE_APPLE_ID" \
      --team-id "$NOTARIZE_TEAM_ID" \
      --password "$NOTARIZE_PASSWORD" >/dev/null 2>&1; then
    ok "notary credentials reachable (history call succeeded)"
  else
    bad "notary credentials FAILED — Apple rejected the auth"
  fi
else
  bad "no notary credentials set"
  echo "     set EXPLOITBOT_NOTARY_PROFILE=<profile-name>  (recommended, keychain-backed)"
  echo "     or NOTARIZE_APPLE_ID + NOTARIZE_TEAM_ID + NOTARIZE_PASSWORD (app-specific password)"
fi

echo ""
echo "== disk =="
free_gib=$(df -g "$ROOT_DIR" | awk 'NR==2 {print $4}')
if (( free_gib < 5 )); then
  bad "only ${free_gib}GiB free at $ROOT_DIR — release build needs >5GiB headroom"
else
  ok "${free_gib}GiB free at $ROOT_DIR"
fi

echo ""
echo "=========================================="
echo "  passed: $pass"
echo "  failed: $fail"
echo "=========================================="

if (( fail > 0 )); then
  echo ""
  echo "Fix the failed items before running ./script/package_release.sh --notarize"
  exit 1
fi

echo ""
echo "Ready. Next step:"
if [[ -n "$NOTARY_PROFILE" ]]; then
  echo "  EXPLOITBOT_NOTARY_PROFILE=\"$NOTARY_PROFILE\" ./script/package_release.sh --notarize"
else
  echo "  NOTARIZE_APPLE_ID=... NOTARIZE_TEAM_ID=... NOTARIZE_PASSWORD=... \\"
  echo "    ./script/package_release.sh --notarize"
fi
