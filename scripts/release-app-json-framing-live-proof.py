#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "release/ExploitBot.app"
APP_BINARY = APP / "Contents/MacOS/ExploitBot"
APP_API_HOST = "127.0.0.1"
APP_API_PORT = 9999
RELEASE_READINESS = ROOT / "docs/live-proofs/2026-07-04-release-readiness.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-release-app-json-framing-live.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def wait_for_app(timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            fetch_json("/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"release app test server did not become ready: {last_error}")


def fetch_json(path: str, timeout: float = 5.0) -> dict[str, Any] | list[Any]:
    parsed, _, _ = fetch_and_parse(path, timeout=timeout)
    return parsed


def fetch_and_parse(path: str, timeout: float = 5.0) -> tuple[dict[str, Any] | list[Any], bytes, dict[str, str]]:
    conn = http.client.HTTPConnection(APP_API_HOST, APP_API_PORT, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        raw = resp.read()
        headers = {key: value for key, value in resp.getheaders()}
        parsed = json.loads(raw.decode("utf-8"))
        return parsed, raw, headers
    finally:
        conn.close()


def process_rows(pattern: str) -> list[str]:
    result = subprocess.run(
        ["ps", "-axo", "pid,rss,command"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    rows = []
    for line in result.stdout.splitlines():
        if pattern in line and "release-app-json-framing-live-proof.py" not in line:
            rows.append(line.strip())
    return rows


def engine_process_rows() -> list[str]:
    needles = ("ExploitBotEngine/launch.py", "vmlx_engine.server", "Qwen3.6", "MiniMax-M", "vllm-mlx")
    result = subprocess.run(
        ["ps", "-axo", "pid,rss,command"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    rows = []
    for line in result.stdout.splitlines():
        if any(needle in line for needle in needles) and "codex" not in line:
            rows.append(line.strip())
    return rows


def poll_json(iterations: int = 240) -> dict[str, Any]:
    invalid: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    state_parsed = 0
    messages_parsed = 0
    max_state_bytes = 0
    content_lengths: list[int] = []
    cache_controls: list[str] = []
    content_length_missing = False
    content_length_mismatch = False
    cache_control_bad = False

    for index in range(iterations):
        for path in ("/state", "/messages"):
            try:
                parsed, raw, headers = fetch_and_parse(path)
                content_length = headers.get("Content-Length")
                cache_control = headers.get("Cache-Control")
                if content_length is None:
                    content_length_missing = True
                    content_length_value = -1
                else:
                    content_length_value = int(content_length)
                    content_lengths.append(content_length_value)
                    if content_length_value != len(raw):
                        content_length_mismatch = True
                if cache_control != "no-store":
                    cache_control_bad = True
                else:
                    cache_controls.append(cache_control)
                if path == "/state":
                    state_parsed += 1
                    max_state_bytes = max(max_state_bytes, len(raw))
                else:
                    messages_parsed += 1
                if index < 3 or index >= iterations - 2:
                    samples.append(
                        {
                            "i": index,
                            "path": path,
                            "bytes": len(raw),
                            "contentLengthHeader": content_length,
                            "contentLengthMatchesBytes": content_length_value == len(raw),
                            "cacheControl": cache_control,
                            "topLevelType": type(parsed).__name__,
                            "parsed": True,
                        }
                    )
            except Exception as exc:
                invalid.append({"i": index, "path": path, "error": f"{type(exc).__name__}: {exc}"})

    return {
        "iterations": iterations,
        "totalResponses": iterations * 2,
        "stateResponsesParsed": state_parsed,
        "messagesResponsesParsed": messages_parsed,
        "invalidCount": len(invalid),
        "invalidSamples": invalid[:10],
        "maxStateBytes": max_state_bytes,
        "contentLengthSamples": content_lengths[:10],
        "cacheControlSamples": cache_controls[:10],
        "sample": samples,
        "contentLengthMissing": content_length_missing,
        "contentLengthMismatch": content_length_mismatch,
        "cacheControlBad": cache_control_bad,
    }


def main() -> None:
    require(APP_BINARY.is_file(), "release/ExploitBot.app binary is missing", str(APP_BINARY))
    require(RELEASE_READINESS.is_file(), "release readiness artifact is missing", str(RELEASE_READINESS))
    release_readiness = json.loads(RELEASE_READINESS.read_text(encoding="utf-8"))
    artifacts = release_readiness.get("artifacts") or {}
    require(release_readiness.get("localPackageStatus") == "PASS", "release readiness local package is not PASS", release_readiness)

    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "release-app-json-framing-live",
        "generatedAt": timestamp(),
    }
    error: Exception | None = None
    try:
        wait_for_app()
        polls = poll_json()
        engines = engine_process_rows()
        app_rows = process_rows(str(APP_BINARY))
        status = {
            "localPackageStatus": "PASS",
            "distributionStatus": release_readiness.get("distributionStatus", "BLOCKED"),
            "contentLengthHeader": "PASS" if not polls["contentLengthMissing"] else "FAIL",
            "contentLengthMatchesBytes": "PASS" if not polls["contentLengthMismatch"] else "FAIL",
            "cacheControlNoStore": "PASS" if not polls["cacheControlBad"] else "FAIL",
            "allStateResponsesParsed": "PASS" if polls["stateResponsesParsed"] == polls["iterations"] else "FAIL",
            "allMessagesResponsesParsed": "PASS" if polls["messagesResponsesParsed"] == polls["iterations"] else "FAIL",
            "noModelProcessSpawned": "PASS" if not engines else "FAIL",
        }
        report.update(
            {
                "ok": all(value == "PASS" for key, value in status.items() if key != "distributionStatus"),
                "releaseReadinessGeneratedAt": release_readiness.get("generatedAt"),
                "app": {
                    "path": "release/ExploitBot.app",
                    "dmgPath": "release/ExploitBot-beta.dmg",
                    "localPackageStatus": release_readiness.get("localPackageStatus"),
                    "distributionStatus": release_readiness.get("distributionStatus"),
                    "binarySha256": artifacts.get("appBinarySha256"),
                    "dmgSha256": artifacts.get("dmgSha256"),
                },
                "appSha256": artifacts.get("appBinarySha256"),
                "dmgSha256": artifacts.get("dmgSha256"),
                "polls": polls,
                "status": status,
                "appProcessRows": app_rows,
                "engineProcessRows": engines,
            }
        )
        require(report["ok"] is True, "release app JSON framing proof did not pass", report)
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)
        DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print(f"release-app-json-framing-live proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, OSError, socket.timeout, json.JSONDecodeError) as exc:
        print(f"release-app-json-framing-live proof failed: {exc}", flush=True)
        raise SystemExit(1)
