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
ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-report-finding-actions-current.json"


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


def assert_report_actions(state: dict, *, count: int, wizard: bool, last_action: str) -> dict:
    actions = state.get("reportFindingActions") or {}
    if actions.get("findingCount") != count:
        raise AssertionError(f"report finding count mismatch: {actions}")
    if actions.get("wizardVisible") is not wizard:
        raise AssertionError(f"report wizard visibility mismatch: {actions}")
    if actions.get("lastAction") != last_action:
        raise AssertionError(f"report last action mismatch: {actions}")
    if actions.get("createLabel") != "Create Finding":
        raise AssertionError(f"report create label missing: {actions}")
    if actions.get("deleteLabel") != "Delete finding":
        raise AssertionError(f"report delete label missing: {actions}")
    return actions


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def build_report(
    *,
    started_at: str,
    finished_at: str,
    seeded: dict,
    opened: dict,
    created: dict,
    deleted: dict,
    final_state: dict,
) -> dict:
    actions = final_state.get("reportFindingActions") or {}
    activity = (final_state.get("tabActivities") or {}).get("report", {})
    finding_id = str(created.get("findingId") or "")
    checks = {
        "seedReportState": passfail(seeded.get("ok") is True),
        "createFinding": passfail(opened.get("ok") is True and actions.get("createLabel") == "Create Finding"),
        "submitFinding": passfail(created.get("ok") is True and bool(finding_id)),
        "deleteFinding": passfail(
            deleted.get("ok") is True
            and actions.get("lastAction") == "deleted"
            and actions.get("lastDeletedId") == finding_id
        ),
        "activityTelemetry": passfail(activity.get("status") == "done" and activity.get("lastTool") == "delete_finding"),
        "wizardDismissed": passfail(actions.get("wizardVisible") is False),
        "modelInferenceStarted": "NO",
    }
    ok = all(v in {"PASS", "NO"} for v in checks.values())
    return {
        "ok": ok,
        "proofType": "report-finding-actions-live",
        "status": "PASS" if ok else "FAIL",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "sourceRoutes": [
            "/qa/seed-report-finding-actions",
            "/qa/report-create-finding",
            "/qa/report-submit-finding",
            "/qa/report-delete-finding",
        ],
        "noModelLoaded": True,
        "checks": checks,
        "createdFindingId": finding_id,
        "reportFindingActions": actions,
        "reportActivity": activity,
    }


def write_report(report: dict) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    started_at = timestamp()
    app = None

    with app_proof_lock("report-finding-actions-proof.py"):
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            seeded = request("POST", "/qa/seed-report-finding-actions")
            if seeded.get("ok") is not True:
                raise AssertionError(f"report finding action seed failed: {seeded}")
            state = request("GET", "/state")
            assert_report_actions(state, count=0, wizard=False, last_action="seeded")
            if state.get("activeTab") != "report":
                raise AssertionError(f"report tab was not activated: {state}")

            opened = request("POST", "/qa/report-create-finding")
            if opened.get("ok") is not True:
                raise AssertionError(f"report create action failed: {opened}")
            state = request("GET", "/state")
            assert_report_actions(state, count=0, wizard=True, last_action="open-create")

            created = request("POST", "/qa/report-submit-finding", {
                "title": "QA Manual Report Finding",
                "target": "https://report-actions.example.test",
                "severity": "high",
                "cve": "CVE-2021-41773",
            })
            finding_id = created.get("findingId")
            if created.get("ok") is not True or not finding_id:
                raise AssertionError(f"report submit action failed: {created}")
            state = request("GET", "/state")
            actions = assert_report_actions(state, count=1, wizard=False, last_action="created")
            rows = actions.get("findings") or []
            if len(rows) != 1 or rows[0].get("title") != "QA Manual Report Finding":
                raise AssertionError(f"created finding row missing from report actions: {actions}")
            if rows[0].get("deleteLabel") != "Delete finding":
                raise AssertionError(f"created finding row lacks delete action label: {actions}")

            deleted = request("POST", "/qa/report-delete-finding", finding_id)
            if deleted.get("ok") is not True:
                raise AssertionError(f"report delete action failed: {deleted}")
            state = request("GET", "/state")
            actions = assert_report_actions(state, count=0, wizard=False, last_action="deleted")
            if actions.get("lastDeletedId") != finding_id:
                raise AssertionError(f"deleted id not exposed: {actions}")
            activity = state.get("tabActivities", {}).get("report", {})
            if activity.get("status") != "done" or activity.get("lastTool") != "delete_finding":
                raise AssertionError(f"report tab did not show delete completion: {activity}")

            report = build_report(
                started_at=started_at,
                finished_at=timestamp(),
                seeded=seeded,
                opened=opened,
                created=created,
                deleted=deleted,
                final_state=state,
            )
            write_report(report)
            print(f"report-finding-actions proof passed: {ARTIFACT}")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app is not None and app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-finding-actions proof failed: {exc}", flush=True)
        raise SystemExit(1)
