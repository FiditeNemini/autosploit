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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 8.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        coverage = request("GET", "/qa/tool-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"tool coverage did not expose ok=true: {coverage}")
        failures = coverage.get("failures", [])
        if failures:
            raise AssertionError(f"tool coverage failures: {failures}")
        if coverage.get("toolCount") != 44:
            raise AssertionError(f"unexpected model tool count: {coverage}")
        if coverage.get("callbackCount") != 3:
            raise AssertionError(f"unexpected callback count: {coverage}")
        if coverage.get("boundedCatalogueLimit") != 12:
            raise AssertionError(f"tool catalogue limit changed: {coverage}")
        required_tabs = {"recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"}
        if set(coverage.get("tabs", [])) != required_tabs:
            raise AssertionError(f"tab coverage mismatch: {coverage}")

        tools = {tool["name"]: tool for tool in coverage.get("tools", [])}
        for name in ("search_context", "search_cve", "lookup_cve"):
            if tools.get(name, {}).get("execution") != "callback":
                raise AssertionError(f"callback tool not marked correctly: {name} {tools.get(name)}")
        for name in ("nmap", "nuclei", "netexec", "hashcat", "metasploit", "impacket", "linpeas", "gowitness", "syft", "grype", "osv_scanner", "run_shell"):
            if tools.get(name, {}).get("execution") != "subprocess":
                raise AssertionError(f"external tool not marked correctly: {name} {tools.get(name)}")
            if name != "run_shell" and not tools.get(name, {}).get("tabs"):
                raise AssertionError(f"external tool has no tab ownership: {name} {tools.get(name)}")

        raw_only = {tool["name"] for tool in coverage.get("tools", []) if tool.get("resultMode") == "raw"}
        for name in ("tshark", "bettercap", "chisel", "pwncat", "sliver", "run_shell"):
            if name not in raw_only:
                raise AssertionError(f"expected raw-only tool not declared raw-only: {name} {tools.get(name)}")

        shell_policy = coverage.get("shellSafetyPolicy") or {}
        run_shell_policy = tools.get("run_shell", {}).get("shellSafety") or {}
        if shell_policy != run_shell_policy:
            raise AssertionError(f"run_shell row policy does not match registry policy: {coverage}")
        if shell_policy.get("tool") != "run_shell":
            raise AssertionError(f"shell policy tool mismatch: {shell_policy}")
        if shell_policy.get("availability") != "alwaysVisible":
            raise AssertionError(f"run_shell must remain visible to agent prompts: {shell_policy}")
        if shell_policy.get("mode") != "allowWithDestructivePatternBlocklist":
            raise AssertionError(f"shell policy mode mismatch: {shell_policy}")
        if shell_policy.get("blockedPatternCount", 0) < 10:
            raise AssertionError(f"shell blocklist too small to audit destructive patterns: {shell_policy}")
        if shell_policy.get("safeSampleAllowed") is not True:
            raise AssertionError(f"safe shell sample should stay allowed: {shell_policy}")
        if shell_policy.get("dangerSampleBlocked") is not True:
            raise AssertionError(f"dangerous shell sample should be blocked: {shell_policy}")
        if shell_policy.get("dangerSamplePattern") != "rm -rf /":
            raise AssertionError(f"danger sample pattern mismatch: {shell_policy}")

        structured = {tool["name"] for tool in coverage.get("tools", []) if tool.get("resultMode") == "structured"}
        for name in ("subfinder", "httpx", "nuclei", "nmap", "sqlmap", "hashcat", "impacket", "linpeas", "gowitness", "graphqlmap", "syft", "grype", "osv_scanner"):
            if name not in structured:
                raise AssertionError(f"expected structured parser missing: {name} {tools.get(name)}")

        print("tool-registry-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tool-registry-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
