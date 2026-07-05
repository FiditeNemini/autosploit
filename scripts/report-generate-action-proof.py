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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-report-generate-action-current.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


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


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def build_report(
    *,
    started_at: str,
    finished_at: str,
    seeded: dict,
    generated: dict,
    final_state: dict,
) -> dict:
    render = final_state.get("reportRenderActions") or {}
    feed = final_state.get("feedRecent") or []
    checks = {
        "seedReportState": passfail(seeded.get("ok") is True),
        "generateAction": passfail(generated.get("ok") is True and render.get("lastAction") == "generate"),
        "renderDone": passfail(render.get("status") == "done"),
        "findingCount": passfail(render.get("findingCount") == 1),
        "generatedPreview": passfail(render.get("htmlChars", 0) > 100 and "QA Report Generate Critical" in render.get("htmlPreview", "")),
        "activityTelemetry": passfail(any("generateReport" in entry.get("text", "") for entry in feed)),
        "modelInferenceStarted": "NO",
    }
    ok = all(v in {"PASS", "NO"} for v in checks.values())
    return {
        "ok": ok,
        "proofType": "report-generate-action-live",
        "status": "PASS" if ok else "FAIL",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "sourceRoutes": ["/qa/seed-report-generate-action", "/qa/report-generate-action"],
        "noModelLoaded": True,
        "checks": checks,
        "reportRenderActions": render,
        "feedRecent": feed[:8],
    }


def write_report(report: dict) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    started_at = timestamp()
    app = None

    with app_proof_lock("report-generate-action-proof.py"):
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            seeded = request("POST", "/qa/seed-report-generate-action")
            if seeded.get("ok") is not True:
                raise AssertionError(f"report generate seed failed: {seeded}")

            generated = request("POST", "/qa/report-generate-action", {"template": "Full Report"})
            if generated.get("ok") is not True:
                raise AssertionError(f"report generate failed: {generated}")
            state = request("GET", "/state")
            render = state.get("reportRenderActions") or {}
            if render.get("lastAction") != "generate" or render.get("status") != "done":
                raise AssertionError(f"report render action state missing: {render}")
            if render.get("findingCount") != 1 or render.get("htmlChars", 0) <= 100:
                raise AssertionError(f"report render did not expose generated HTML size/count: {render}")
            if "QA Report Generate Critical" not in render.get("htmlPreview", ""):
                raise AssertionError(f"report render preview missing finding title: {render}")
            feed = state.get("feedRecent") or []
            if not any("generateReport" in entry.get("text", "") for entry in feed):
                raise AssertionError(f"report generate not visible in activity feed: {feed}")

            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                seeded=seeded,
                generated=generated,
                final_state=state,
            )
            write_report(report)
            print(f"report-generate-action proof passed: {ARTIFACT}")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app is not None and app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-generate-action proof failed: {exc}", flush=True)
        raise SystemExit(1)
