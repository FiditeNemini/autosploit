#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Applications/vMLX.app/Contents/Resources/bundled-python/python/bin/python3}"
PORT="${PORT:-8130}"
HOST="127.0.0.1"
BASE_URL="http://${HOST}:${PORT}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python runtime not found: $PYTHON_BIN" >&2
  exit 2
fi

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $PORT is already in use" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d)"
LOG_FILE="$TMP_DIR/uvicorn.log"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

PYTHONPATH="$ROOT/ExploitBotEngine" "$PYTHON_BIN" -m uvicorn \
  vmlx_engine.server:app \
  --host "$HOST" \
  --port "$PORT" \
  >"$LOG_FILE" 2>&1 &
SERVER_PID="$!"

for _ in {1..50}; do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "Server exited before health was available" >&2
    cat "$LOG_FILE" >&2
    exit 1
  fi
  sleep 0.2
done

HEALTH_JSON="$(curl -fsS "$BASE_URL/health")"
CACHE_JSON="$(curl -fsS "$BASE_URL/v1/cache/stats")"
MODELS_JSON="$(curl -fsS "$BASE_URL/v1/models")"

"$PYTHON_BIN" - "$HEALTH_JSON" "$CACHE_JSON" "$MODELS_JSON" <<'PY'
import json
import sys

health = json.loads(sys.argv[1])
cache = json.loads(sys.argv[2])
models = json.loads(sys.argv[3])

effective = health.get("effective_config") or {}
cache_config = effective.get("cache") or {}
required_cache_keys = {
    "prefix_cache",
    "paged_cache",
    "kv_cache_quantization",
    "disk_cache",
    "ssm_companion",
}
missing = sorted(required_cache_keys - set(cache_config))
if missing:
    raise SystemExit(f"missing effective cache keys: {missing}")
if health.get("status") != "no_model":
    raise SystemExit(f"expected no_model status, got {health.get('status')!r}")
if "memory" not in cache:
    raise SystemExit("cache stats response did not include memory diagnostics")
if models.get("object") != "list" or not isinstance(models.get("data"), list):
    raise SystemExit("models response is not OpenAI-compatible list shape")

print("health.status=", health["status"], sep="")
print("effective.cache.keys=", ",".join(sorted(cache_config)), sep="")
print("cache.keys=", ",".join(sorted(cache)), sep="")
print("models.count=", len(models["data"]), sep="")
PY
