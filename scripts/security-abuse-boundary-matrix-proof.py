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

EXPECTED_ROWS = [
    "authorizedPentestTooling",
    "destructiveShellBlocklist",
    "agentAuthorizationModes",
    "supplyChainCVEGuardrails",
    "promptContextBoundary",
    "evidenceAuditLogging",
]

EXPECTED_CONTRACTS = {
    "offensiveToolCoverage",
    "shellDangerSampleBlocked",
    "authorizationPolicyParity",
    "cveIncludeOnlyImport",
    "promptInjectionBoundary",
    "auditAndToolStatusLogging",
}

EXPECTED_PROOFS = {
    "security-abuse-boundary-matrix-proof.py",
    "tool-registry-coverage-proof.py",
    "agent-tool-authorization-proof.py",
    "context-prompt-injection-boundary-proof.py",
    "cve-import-embedding-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "audit-ledger-proof.py",
}

REQUIRED_TOOLING = {
    "nmap",
    "nuclei",
    "sqlmap",
    "metasploit",
    "impacket",
    "netexec",
    "hashcat",
    "hydra",
    "trufflehog",
    "syft",
    "grype",
    "osv_scanner",
    "run_shell",
}


def request(method: str, path: str, body: str | dict | None = None, timeout: float = 45.0):
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

        matrix = request("GET", "/qa/security-abuse-boundary-matrix")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"security boundary matrix failed: {matrix}")
        if matrix.get("proofLevel") != "authorization-shell-cve-context-audit-backed":
            raise AssertionError(f"security boundary proof level mismatch: {matrix}")
        if matrix.get("rows") != EXPECTED_ROWS:
            raise AssertionError(f"security boundary row list mismatch: {matrix}")
        if matrix.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"security boundary row count mismatch: {matrix}")

        contracts = matrix.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"security boundary missing contracts {missing_contracts}: {matrix}")
        if matrix.get("contractParity") is not True:
            raise AssertionError(f"security boundary contract parity mismatch: {matrix}")

        tool_names = set(matrix.get("authorizedToolNames") or [])
        missing_tools = sorted(REQUIRED_TOOLING.difference(tool_names))
        if missing_tools:
            raise AssertionError(f"security boundary missing offensive tooling {missing_tools}: {matrix}")
        if matrix.get("authorizedToolCount", 0) < len(REQUIRED_TOOLING):
            raise AssertionError(f"security boundary authorized tool count too low: {matrix}")

        shell = matrix.get("shellSafetyPolicy") or {}
        if shell.get("mode") != "allowWithDestructivePatternBlocklist":
            raise AssertionError(f"security boundary shell mode mismatch: {matrix}")
        if shell.get("dangerSampleBlocked") is not True:
            raise AssertionError(f"security boundary did not block destructive shell sample: {matrix}")
        if shell.get("safeSampleAllowed") is not True:
            raise AssertionError(f"security boundary should allow safe shell sample: {matrix}")
        if matrix.get("authorizationPolicyCount") != 3:
            raise AssertionError(f"security boundary authorization policy count mismatch: {matrix}")
        if matrix.get("cveIncludeFilterMode") != "includeOnly-cve-id-allowlist":
            raise AssertionError(f"security boundary CVE include filter mismatch: {matrix}")
        if matrix.get("promptInjectionPolicy") != "search-on-demand-not-force-injected":
            raise AssertionError(f"security boundary prompt policy mismatch: {matrix}")
        if matrix.get("toolStatusSurfaceCount", 0) < 4:
            raise AssertionError(f"security boundary tool status surfaces too thin: {matrix}")
        if matrix.get("auditProofFileParity") is not True:
            raise AssertionError(f"security boundary audit proof parity mismatch: {matrix}")

        proofs = set(matrix.get("proofs") or [])
        missing_proofs = sorted(EXPECTED_PROOFS.difference(proofs))
        if missing_proofs:
            raise AssertionError(f"security boundary missing proofs {missing_proofs}: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"security boundary proof-file parity mismatch: {matrix}")

        state_routes = (request("GET", "/state").get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/security-abuse-boundary-matrix" not in state_routes:
            raise AssertionError(f"state route list missing security boundary route: {state_routes}")

        tools_group = (index.get("groups") or {}).get("toolsAndParsers") or {}
        if "/qa/security-abuse-boundary-matrix" not in (tools_group.get("endpoints") or []):
            raise AssertionError(f"coverage index missing security boundary endpoint: {tools_group}")
        if tools_group.get("securityBoundaryRows") != EXPECTED_ROWS:
            raise AssertionError(f"coverage index security boundary row mismatch: {tools_group}")
        if tools_group.get("securityBoundaryContractParity") is not True:
            raise AssertionError(f"coverage index security boundary parity mismatch: {tools_group}")
        if tools_group.get("securityBoundaryProofFileParity") is not True:
            raise AssertionError(f"coverage index security boundary proof parity mismatch: {tools_group}")

        print("security-abuse-boundary-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"security-abuse-boundary-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
