#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("GET", "/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"app test server did not become ready: {last_error}")


def assert_cache_policy(policy: dict, expected_generation: int) -> None:
    if policy.get("generation") != expected_generation:
        raise AssertionError(f"wrong context generation: {policy}")
    if policy.get("engineSessionPreserved") is not True:
        raise AssertionError(f"new context must preserve engine session: {policy}")
    if policy.get("cacheResponsesMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"missing cache-response inference marker: {policy}")
    required = {
        "prefixCache": True,
        "promptL2Disk": True,
        "pagedCache": True,
        "blockL2Disk": True,
        "turboQuantKV": True,
        "modelGenerationDefaults": True,
    }
    for key, expected in required.items():
        if policy.get(key) is not expected:
            raise AssertionError(f"context cache policy {key}={policy.get(key)!r}; expected {expected!r}: {policy}")


def run(output: Path | None = None) -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-settings-visual-state")
        if seeded.get("ok") is not True:
            raise AssertionError(f"settings visual seed failed: {seeded}")

        before = request("GET", "/state")
        before_policy = before.get("contextWindow")
        if not isinstance(before_policy, dict):
            raise AssertionError(f"missing contextWindow policy before new context: {before}")
        assert_cache_policy(before_policy, expected_generation=0)

        before_stats = before.get("engineCacheStats")
        if not before_stats:
            raise AssertionError(f"missing cache stats before new context: {before}")

        cleared = request("POST", "/context/new")
        if cleared.get("ok") is not True:
            raise AssertionError(f"context/new failed: {cleared}")

        after = request("GET", "/state")
        after_policy = after.get("contextWindow")
        if not isinstance(after_policy, dict):
            raise AssertionError(f"missing contextWindow policy after new context: {after}")
        assert_cache_policy(after_policy, expected_generation=1)

        messages = request("GET", "/messages")
        if messages != []:
            raise AssertionError(f"new context did not clear visible messages: {messages}")
        metrics = after.get("metrics") or {}
        if metrics.get("promptTokens") != 0 or metrics.get("completionTokens") != 0 or metrics.get("cachedTokens") != 0:
            raise AssertionError(f"new context did not reset chat-local counters: {metrics}")
        if (after.get("requestContext") or {}).get("contextInjected") is not False:
            raise AssertionError(f"new context did not clear previous request context: {after.get('requestContext')}")
        if after.get("engineConfig") != before.get("engineConfig"):
            raise AssertionError(f"new context changed engine config: before={before.get('engineConfig')} after={after.get('engineConfig')}")
        if after.get("engineCacheStats") != before_stats:
            raise AssertionError("new context cleared or changed engine cache stats")

        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "context_window_before": before_policy,
                        "context_window_after": after_policy,
                        "engine_config_preserved": after.get("engineConfig") == before.get("engineConfig"),
                        "engine_cache_stats_preserved": after.get("engineCacheStats") == before_stats,
                        "messages_after_new_context": len(messages),
                        "metrics_after_new_context": metrics,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        print("context-window-cache proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        run(args.output)
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"context-window-cache proof failed: {exc}", flush=True)
        raise SystemExit(1)
