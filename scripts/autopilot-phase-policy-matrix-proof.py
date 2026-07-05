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


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 8.0):
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

        matrix = request("GET", "/qa/autopilot-phase-policy-matrix")
        if matrix.get("ok") is not True or matrix.get("decisionParity") is not True:
            raise AssertionError(f"autopilot phase policy matrix failed: {matrix}")
        if matrix.get("policyContract") != "high-risk-external-targets-require-scope-or-authorization":
            raise AssertionError(f"wrong policy contract: {matrix}")

        phases = {row.get("phase"): row for row in matrix.get("phaseRows") or []}
        for phase in ("scan", "detect", "breach"):
            if phase not in phases:
                raise AssertionError(f"missing phase {phase}: {matrix}")
            controls = set(phases[phase].get("requiredControls") or [])
            for control in ("explicitToolDeny", "scopeOrAuthorizationForExternalTargets"):
                if control not in controls:
                    raise AssertionError(f"missing {control} for {phase}: {matrix}")

        decisions = matrix.get("decisions") or {}
        blocked = decisions.get("noScopeExternalNmap") or {}
        if blocked.get("decision") != "blocked":
            raise AssertionError(f"noScopeExternalNmap should be blocked: {matrix}")
        if "requires an Op scope or explicit authorization" not in blocked.get("reason", ""):
            raise AssertionError(f"block reason missing scope/authorization text: {matrix}")

        for name in ("localLoopbackNmap", "authorizedExternalNmap", "scopedExternalNmap"):
            if (decisions.get(name) or {}).get("decision") != "allowed":
                raise AssertionError(f"{name} should be allowed: {matrix}")

        high_risk = set(matrix.get("highRiskAutopilotTools") or [])
        for tool in ("nmap", "sqlmap", "hydra", "metasploit", "sliver", "run_shell"):
            if tool not in high_risk:
                raise AssertionError(f"high-risk tool missing {tool}: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"policy matrix proof file parity failed: {matrix}")

        print("autopilot-phase-policy-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"autopilot-phase-policy-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
