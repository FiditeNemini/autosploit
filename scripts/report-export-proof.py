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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-report-export-current.json"


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


def assert_artifact(path: Path, min_bytes: int, must_contain: bytes | None = None) -> None:
    if not path.exists():
        raise AssertionError(f"missing report artifact: {path}")
    data = path.read_bytes()
    if len(data) < min_bytes:
        raise AssertionError(f"report artifact too small: {path} ({len(data)} bytes)")
    if must_contain is not None and must_contain not in data:
        raise AssertionError(f"report artifact missing marker {must_contain!r}: {path}")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def build_report(
    *,
    started_at: str,
    finished_at: str,
    seeded: dict,
    final_state: dict,
    artifact_checks: dict[str, bool],
) -> dict:
    export = final_state.get("reportExport") or {}
    artifacts = export.get("artifacts") or []
    by_format = {item.get("format"): item for item in artifacts}
    checks = {
        "seedReportState": passfail(seeded.get("ok") is True),
        "exportStatus": passfail(export.get("status") == "done"),
        "findingCount": passfail(export.get("findingCount") == 1),
        "htmlArtifact": passfail(artifact_checks.get("html") is True and by_format.get("html", {}).get("exists") is True),
        "markdownArtifact": passfail(artifact_checks.get("markdown") is True and by_format.get("markdown", {}).get("exists") is True),
        "jsonArtifact": passfail(artifact_checks.get("json") is True and by_format.get("json", {}).get("exists") is True),
        "pdfArtifact": passfail(artifact_checks.get("pdf") is True and by_format.get("pdf", {}).get("exists") is True),
        "modelInferenceStarted": "NO",
    }
    ok = all(v in {"PASS", "NO"} for v in checks.values())
    return {
        "ok": ok,
        "proofType": "report-export-live",
        "status": "PASS" if ok else "FAIL",
        "generatedAt": finished_at,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "sourceRoutes": ["/qa/seed-report-export", "/qa/report-export-action"],
        "noModelLoaded": True,
        "checks": checks,
        "reportExport": export,
        "artifactChecks": artifact_checks,
    }


def write_report(report: dict) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    started_at = timestamp()
    app = None

    with app_proof_lock("report-export-proof.py"):
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            with tempfile.TemporaryDirectory(prefix="exploitbot-report-proof-") as tmp:
                out_dir = Path(tmp)
                seeded = request("POST", "/qa/seed-report-export", {"outputDir": str(out_dir)})
                if seeded.get("ok") is not True:
                    raise AssertionError(f"report export seed failed: {seeded}")

                state = request("GET", "/state")
                report = state.get("reportExport") or {}
                if report.get("status") != "done":
                    raise AssertionError(f"report export did not finish: {report}")
                if report.get("findingCount") != 1:
                    raise AssertionError(f"report export did not use seeded finding: {report}")
                artifacts = report.get("artifacts") or []
                formats = {a.get("format"): a for a in artifacts}
                for fmt in ("html", "markdown", "json", "pdf"):
                    artifact = formats.get(fmt)
                    if not artifact:
                        raise AssertionError(f"missing {fmt} artifact metadata: {report}")
                    if artifact.get("exists") is not True or artifact.get("bytes", 0) <= 0:
                        raise AssertionError(f"{fmt} artifact not validated: {artifact}")

                html = Path(formats["html"]["path"])
                md = Path(formats["markdown"]["path"])
                js = Path(formats["json"]["path"])
                pdf = Path(formats["pdf"]["path"])
                artifact_checks = {
                    "html": True,
                    "markdown": True,
                    "json": True,
                    "pdf": True,
                }
                assert_artifact(html, 1000, b"QA Report Proof Critical")
                assert_artifact(md, 300, b"QA Report Proof Critical")
                assert_artifact(js, 200, b"QA Report Proof Critical")
                assert_artifact(pdf, 300, b"%PDF")

                durable_state = dict(state)
                durable_export = dict(report)
                durable_export["artifacts"] = [
                    {**artifact, "path": Path(artifact["path"]).name}
                    for artifact in artifacts
                ]
                durable_state["reportExport"] = durable_export
                proof_report = build_report(
                    started_at=started_at,
                    finished_at=timestamp(),
                    seeded=seeded,
                    final_state=durable_state,
                    artifact_checks=artifact_checks,
                )
                write_report(proof_report)
            print(f"report-export proof passed: {ARTIFACT}")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app is not None and app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"report-export proof failed: {exc}", flush=True)
        raise SystemExit(1)
