#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-run}"
APP_NAME="ExploitBot"
BUNDLE_ID="ai.jangq.ExploitBot"
MIN_SYSTEM_VERSION="14.0"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/ExploitBot"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
APP_BINARY="$APP_MACOS/$APP_NAME"
INFO_PLIST="$APP_CONTENTS/Info.plist"
ENGINE_LAUNCH="$ROOT_DIR/ExploitBotEngine/launch.py"
ENGINE_PID_FILE="$HOME/.exploitbot/engine.pid"
APP_PROOF_LOCK_DIR="$ROOT_DIR/.proof-locks"
APP_PROOF_LOCK_PATH="$APP_PROOF_LOCK_DIR/app-launch.lock"

cleanup_stale_engines() {
  if [[ -f "$ENGINE_PID_FILE" ]]; then
    pid="$(tr -cd '0-9' <"$ENGINE_PID_FILE" || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" -o command= 2>/dev/null | grep -Eq 'ExploitBotEngine/launch.py|vmlx_engine.server'; then
      echo "Stopping stale ExploitBot engine pid $pid..."
      kill -TERM "$pid" >/dev/null 2>&1 || true
      sleep 2
      kill -KILL "$pid" >/dev/null 2>&1 || true
    fi
    if [[ -z "${pid:-}" ]] || ! ps -p "$pid" >/dev/null 2>&1; then
      rm -f "$ENGINE_PID_FILE"
    fi
  fi
  if [[ -f "$ENGINE_LAUNCH" ]] && pgrep -f "$ENGINE_LAUNCH" >/dev/null 2>&1; then
    echo "Skipping untracked ExploitBot engine processes; only $ENGINE_PID_FILE is app-owned."
  fi
}

stale_app_proof_lock_pid() {
  local owner_pid=""
  if [[ ! -f "$APP_PROOF_LOCK_PATH/owner" ]]; then
    local lock_mtime
    local now
    local owner_missing_seconds
    lock_mtime="$(stat -f %m "$APP_PROOF_LOCK_PATH" 2>/dev/null || echo 0)"
    now="$(date +%s)"
    owner_missing_seconds=$((now - lock_mtime))
    # Treat a new ownerless lock as an active writer grace period. Another
    # launcher may have created the directory and not written owner metadata yet.
    if (( owner_missing_seconds < 30 )); then
      return 1
    fi
    return 0
  fi
  if [[ -f "$APP_PROOF_LOCK_PATH/owner" ]]; then
    owner_pid="$(awk -F= '$1 == "appPid" { print $2; exit }' "$APP_PROOF_LOCK_PATH/owner" 2>/dev/null || true)"
    if [[ -z "$owner_pid" ]]; then
      owner_pid="$(awk -F= '$1 == "pid" { print $2; exit }' "$APP_PROOF_LOCK_PATH/owner" 2>/dev/null || true)"
    fi
  fi
  if [[ -n "$owner_pid" ]] && ps -p "$owner_pid" >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

acquire_app_proof_lock() {
  mkdir -p "$APP_PROOF_LOCK_DIR"
  local waited_seconds=0
  while ! mkdir "$APP_PROOF_LOCK_PATH" 2>/dev/null; do
    if stale_app_proof_lock_pid; then
      rm -rf "$APP_PROOF_LOCK_PATH"
      continue
    fi
    if (( waited_seconds == 0 )); then
      echo "Another app-backed proof is using dist/ExploitBot.app; waiting for $APP_PROOF_LOCK_PATH..." >&2
    fi
    if (( waited_seconds >= 300 )); then
      echo "Timed out waiting for app proof lock: $APP_PROOF_LOCK_PATH" >&2
      if [[ -f "$APP_PROOF_LOCK_PATH/owner" ]]; then
        cat "$APP_PROOF_LOCK_PATH/owner" >&2 || true
      fi
      return 1
    fi
    sleep 1
    waited_seconds=$((waited_seconds + 1))
  done
  {
    echo "pid=$$"
    echo "mode=$MODE"
    date "+startedAt=%Y-%m-%dT%H:%M:%S%z"
  } >"$APP_PROOF_LOCK_PATH/owner"
}

release_app_proof_lock() {
  rm -rf "$APP_PROOF_LOCK_PATH"
}

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

build_dist_app() {
  cleanup_stale_engines
  pkill -x "$APP_NAME" >/dev/null 2>&1 || true

  swift build --package-path "$PACKAGE_DIR"
  BUILD_BINARY="$(swift build --package-path "$PACKAGE_DIR" --show-bin-path)/$APP_NAME"

  rm -rf "$APP_BUNDLE"
  mkdir -p "$APP_MACOS"
  mkdir -p "$APP_RESOURCES"
  cp "$BUILD_BINARY" "$APP_BINARY"
  chmod +x "$APP_BINARY"
  if [[ -d "$PACKAGE_DIR/Resources" ]]; then
    rsync -a --delete "$PACKAGE_DIR/Resources/" "$APP_RESOURCES/"
  fi

  # Iter36 P0: copy the SPM-generated resource bundle
  # (`ExploitBot_ExploitBot.bundle` — contains prompts/tabs/*.md exposed
  # via Bundle.module) into the .app. Without this, ChatService's
  # tabPromptContext() gets nil from Bundle.module.url and used to hit
  # fatalError (fixed 2026-07-13 to degrade to nil), which crashed the
  # app every autopilot chain the moment a tab-scoped prompt was needed.
  BIN_DIR="$(swift build --package-path "$PACKAGE_DIR" --show-bin-path)"
  SPM_BUNDLE="$BIN_DIR/ExploitBot_ExploitBot.bundle"
  if [[ -d "$SPM_BUNDLE" ]]; then
    rsync -a --delete "$SPM_BUNDLE" "$APP_RESOURCES/"
  fi

  cat >"$INFO_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>$MIN_SYSTEM_VERSION</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST
}

run_selected_mode() {
  build_dist_app

  case "$MODE" in
    run)
      open_app
      ;;
    --debug|debug)
      lldb -- "$APP_BINARY"
      ;;
    --logs|logs)
      open_app
      /usr/bin/log stream --info --style compact --predicate "process == \"$APP_NAME\""
      ;;
    --telemetry|telemetry)
      open_app
      /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
      ;;
    --verify|verify)
      if [[ "${EXPLOITBOT_TESTING:-0}" == "1" ]]; then
        "$APP_BINARY" >/dev/null 2>&1 &
      else
        open_app
      fi
      sleep 1
      pgrep -x "$APP_NAME" >/dev/null
      ;;
    --build-only|build-only)
      ;;
    *)
      echo "usage: $0 [run|--debug|--logs|--telemetry|--verify|--build-only]" >&2
      exit 2
      ;;
  esac
}

serialize_app_launch() {
  if [[ "${EXPLOITBOT_SKIP_APP_PROOF_LOCK:-0}" == "1" ]]; then
    run_selected_mode
    return
  fi

  acquire_app_proof_lock
  trap release_app_proof_lock EXIT INT TERM
  run_selected_mode
}

serialize_app_launch
