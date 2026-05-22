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


def assert_export(action: str, out_dir: Path) -> None:
    exported = request("POST", "/qa/report-export-action", {
        "action": action,
        "outputDir": str(out_dir),
    })
    if exported.get("ok") is not True:
        raise AssertionError(f"report {action} export failed: {exported}")
    state = request("GET", "/state")
    report = state.get("reportExport") or {}
    if report.get("status") != "done" or report.get("findingCount") != 1:
        raise AssertionError(f"report export state missing after {action}: {report}")
    formats = {item.get("format"): item for item in report.get("artifacts") or []}
    if not {"html", "markdown", "json", "pdf"}.issubset(formats):
        raise AssertionError(f"report export artifacts incomplete after {action}: {report}")
    for artifact in formats.values():
        if artifact.get("exists") is not True or artifact.get("bytes", 0) <= 0:
            raise AssertionError(f"report artifact invalid after {action}: {artifact}")
    feed = state.get("feedRecent") or []
    if not any(action in entry.get("text", "") for entry in feed):
        raise AssertionError(f"report {action} export not visible in activity feed: {feed}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        seeded = request("POST", "/qa/seed-report-generate-action")
        if seeded.get("ok") is not True:
            raise AssertionError(f"report export seed failed: {seeded}")
        request("POST", "/qa/report-generate-action", {"template": "Full Report"})

        with tempfile.TemporaryDirectory(prefix="exploitbot-report-visible-export-") as tmp:
            out_dir = Path(tmp)
            assert_export("exportMarkdown", out_dir)
            assert_export("exportPDF", out_dir)

        print("report-visible-export-actions proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-visible-export-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
