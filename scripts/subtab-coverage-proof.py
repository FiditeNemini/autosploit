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

EXPECTED = {
    "recon": ("Subdomains", ["Subdomains", "Ports", "Web Hosts", "Crawl", "OSINT"], "recon-subtab-state-proof.py"),
    "web": ("Vulns", ["Vulns", "SQLi", "XSS", "Dirs", "Params", "SSL", "JWT"], "web-subtab-state-proof.py"),
    "network": ("Protocols", ["Protocols", "SNMP", "Capture", "MITM", "Tunnels"], "network-subtab-state-proof.py"),
    "creds": ("Cracking", ["Cracking", "Online Brute", "Secrets", "Vault"], "creds-subtab-state-proof.py"),
    "exploit": ("Metasploit", ["Metasploit", "Reverse Shells", "Custom", "C2 (Sliver)"], "exploit-subtab-state-proof.py"),
    "post": ("PrivEsc", ["PrivEsc", "AD Attacks", "Lateral"], "post-subtab-state-proof.py"),
    "supplyChain": ("CVE Intel", ["CVE Intel", "Secrets", "SBOM", "Dependencies"], "supply-chain-cve-ui-proof.py"),
    "osint": ("Username", ["Username", "Email", "Metadata", "Screenshots"], "osint-subtab-state-proof.py"),
    "report": ("Findings", ["Findings", "Preview"], "report-subtab-state-proof.py"),
}

EXPECTED_ROUTES = {
    "/qa/tool-subtab",
    "/qa/visual-subtab",
}


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

        coverage = request("GET", "/qa/subtab-coverage")
        if coverage.get("ok") is not True:
            raise AssertionError(f"subtab coverage route failed: {coverage}")
        tabs = coverage.get("tabs") or {}
        if sorted(tabs) != sorted(EXPECTED):
            raise AssertionError(f"subtab coverage tabs mismatch: {tabs}")
        if sorted(coverage.get("proofs") or []) != sorted(proof for _, _, proof in EXPECTED.values()):
            raise AssertionError(f"subtab coverage proof list mismatch: {coverage}")
        if coverage.get("proofCount", 0) < len(EXPECTED):
            raise AssertionError(f"subtab coverage proof count mismatch: {coverage}")
        missing_files = sorted(proof for _, _, proof in EXPECTED.values() if not (ROOT / "scripts" / proof).is_file())
        if missing_files:
            raise AssertionError(f"subtab coverage names non-existent proof files: {missing_files}")
        if coverage.get("proofFileParity") is not True:
            raise AssertionError(f"subtab coverage proof file parity mismatch: {coverage}")
        missing_routes = sorted(EXPECTED_ROUTES.difference(set(coverage.get("routes") or [])))
        if missing_routes:
            raise AssertionError(f"subtab coverage missing routes {missing_routes}: {coverage}")

        for tab, (default, valid, proof) in EXPECTED.items():
            entry = tabs.get(tab) or {}
            if entry.get("default") != default:
                raise AssertionError(f"{tab} default mismatch: {entry}")
            if entry.get("active") != default:
                raise AssertionError(f"{tab} active default mismatch: {entry}")
            if entry.get("validSubtabs") != valid:
                raise AssertionError(f"{tab} valid subtab list mismatch: {entry}")
            if entry.get("proof") != proof:
                raise AssertionError(f"{tab} proof mismatch: {entry}")
            if entry.get("count") != len(valid):
                raise AssertionError(f"{tab} count mismatch: {entry}")

        switched = request("POST", "/qa/tool-subtab", {"tab": "web", "subtab": "JWT"})
        if switched.get("ok") is not True:
            raise AssertionError(f"web subtab switch failed: {switched}")
        coverage = request("GET", "/qa/subtab-coverage")
        if ((coverage.get("tabs") or {}).get("web") or {}).get("active") != "JWT":
            raise AssertionError(f"subtab coverage did not reflect live active web subtab: {coverage}")

        print("subtab-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"subtab-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
