#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
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


def require_contains(values: list[str], expected: str, label: str) -> None:
    if not any(expected in value for value in values):
        raise AssertionError(f"{label} missing {expected}: {values}")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="exploitbot-parser-home-") as home:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = home
        env["EXPLOITBOT_DATA_DIR"] = str(Path(home) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            seeded = request("POST", "/qa/seed-result-parser-fixture")
            if seeded.get("ok") is not True:
                raise AssertionError(f"result parser fixture seed failed: {seeded}")

            coverage = request("GET", "/qa/result-parser-coverage")
            failures = coverage.get("failures") or []
            if failures:
                raise AssertionError(f"result parser coverage failures: {failures}")

            counts = coverage.get("counts") or {}
            expected_minimums = {
                "subdomains": 3,
                "webHosts": 4,
                "vulns": 15,
                "ports": 2,
                "networkHosts": 2,
                "osint": 6,
                "postAttribution": 3,
                "rawResults": 35,
            }
            for key, minimum in expected_minimums.items():
                if counts.get(key, 0) < minimum:
                    raise AssertionError(f"{key} count too low: {coverage}")

            parsed_tools = set(coverage.get("parsedTools") or [])
            for name in (
                "subfinder", "dnsx", "httpx", "nuclei", "nmap", "katana",
                "feroxbuster", "ffuf", "dalfox", "sqlmap", "haiti",
                "trufflehog", "holehe", "exiftool", "masscan", "netexec",
                "hydra", "wpscan", "testssl", "theharvester", "arjun",
                "jwt_tool", "hashcat", "snmpwalk", "metasploit", "impacket",
                "linpeas", "gowitness", "graphqlmap",
            ):
                if name not in parsed_tools:
                    raise AssertionError(f"structured parser did not emit tab state for {name}: {coverage}")

            raw_only = set(coverage.get("rawOnlyTools") or [])
            for name in ("tshark", "bettercap", "chisel", "pwncat", "sliver"):
                if name not in raw_only:
                    raise AssertionError(f"raw-only tool was not preserved as raw output: {coverage}")

            require_contains(coverage.get("subdomains") or [], "api.qa.example.test", "subdomains")
            require_contains(coverage.get("webUrls") or [], "https://qa.example.test/login", "web hosts")
            require_contains(coverage.get("vulnSources") or [], "nuclei", "vuln sources")
            require_contains(coverage.get("vulnSources") or [], "hashcat", "vuln sources")
            require_contains(coverage.get("networkHosts") or [], "10.0.0.10", "network hosts")
            require_contains(coverage.get("osintPlatforms") or [], "Screenshot", "osint platforms")
            require_contains(coverage.get("postLabels") or [], "impacket-secretsdump", "post labels")

            results = request("GET", "/results")
            if not any(port.get("port") == 443 and port.get("service") == "https" for port in results.get("ports", [])):
                raise AssertionError(f"/results did not expose parsed nmap port: {results}")
            if not any(item.get("platform") == "Screenshot" and item.get("previewKind") == "image" for item in results.get("osint", [])):
                raise AssertionError(f"/results did not expose screenshot artifact: {results}")

            print("result-parser-routing proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"result-parser-routing proof failed: {exc}", flush=True)
        raise SystemExit(1)
