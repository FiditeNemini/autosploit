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


def require_contains(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"{label} missing {needle!r}:\n{haystack}")


def require_not_contains(haystack: str, needle: str, label: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{label} unexpectedly contained {needle!r}:\n{haystack}")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="exploitbot-result-context-home-") as home:
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

            post_packet = request("POST", "/qa/context-packet", {
                "query": "linpeas qa-linux-01 www-data privilege escalation attribution",
                "maxSnippets": 4,
                "includeAssets": True,
                "includeFindings": True,
                "includeRecentToolOutput": True,
                "includeStash": False,
                "cveMode": "off",
            })["packet"]
            require_contains(post_packet, "[post.attribution]", "post attribution catalogue item")
            require_contains(post_packet, "qa-linux-01", "post attribution host")
            require_contains(post_packet, "www-data", "post attribution user")
            require_contains(post_packet, "linpeas-host", "post attribution label")
            require_not_contains(post_packet, "Selected snippets: none yet.", "post attribution query")

            cred_packet = request("POST", "/qa/context-packet", {
                "query": "Password123 hashcat cracked credential",
                "maxSnippets": 4,
                "includeAssets": True,
                "includeFindings": True,
                "includeRecentToolOutput": True,
                "includeStash": False,
                "cveMode": "off",
            })["packet"]
            require_contains(cred_packet, "Password123", "credential finding")
            require_contains(cred_packet, "hashcat", "credential source")

            apache_packet = request("POST", "/qa/context-packet", {
                "query": "443 tcp https Apache 2.4.49 service port",
                "maxSnippets": 4,
                "includeAssets": True,
                "includeFindings": False,
                "includeRecentToolOutput": True,
                "includeStash": False,
                "cveMode": "off",
            })["packet"]
            require_contains(apache_packet, "443/tcp", "nmap parsed asset")

            cve_packet = request("POST", "/qa/context-packet", {
                "query": "Apache 2.4.49 CVE-2021-41773 nuclei path traversal",
                "maxSnippets": 4,
                "includeAssets": True,
                "includeFindings": True,
                "includeRecentToolOutput": True,
                "includeStash": False,
                "cveMode": "off",
            })["packet"]
            require_contains(cve_packet, "CVE-2021-41773", "nuclei parsed finding")

            state = request("GET", "/state")
            embeddings = state.get("catalogEmbeddings") or {}
            sources = set(embeddings.get("sources") or [])
            for source in ("asset.port", "finding", "post.attribution"):
                if source not in sources:
                    raise AssertionError(f"catalog embedding source missing {source}: {embeddings}")

            print("result-context-catalog proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"result-context-catalog proof failed: {exc}", flush=True)
        raise SystemExit(1)
