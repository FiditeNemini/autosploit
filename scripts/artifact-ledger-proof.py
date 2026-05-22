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


def request(method: str, path: str, body: str | None = None, timeout: float = 8.0):
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


def expected_visual_manifests() -> list[Path]:
    return sorted((ROOT / "docs" / "visual-proofs").glob("checkpoint-*/manifest.json"))


def expected_live_proofs() -> list[Path]:
    return sorted((ROOT / "docs" / "live-proofs").glob("*.json"))


def live_proof_ok(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("ok") is True or payload.get("status") == "passed"


def manifest_capture_count(manifests: list[Path]) -> int:
    count = 0
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("ok") is not True:
            raise AssertionError(f"visual manifest is not ok: {manifest.relative_to(ROOT)}")
        captures = payload.get("captures") or []
        count += len(captures)
        missing = [capture for capture in captures if not (ROOT / capture).is_file()]
        if missing:
            raise AssertionError(f"visual manifest names missing captures: {manifest.relative_to(ROOT)} {missing}")
    return count


def assert_artifact_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/artifact-ledger")
    manifests = expected_visual_manifests()
    live_proofs = expected_live_proofs()
    capture_count = manifest_capture_count(manifests)

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/artifact-ledger failed: {ledger}")
    if ledger.get("visualManifestCount") != len(manifests):
        raise AssertionError(f"artifact ledger visual manifest count mismatch: {ledger}")
    if ledger.get("visualCaptureCount") != capture_count:
        raise AssertionError(f"artifact ledger visual capture count mismatch expected {capture_count}: {ledger}")
    if ledger.get("missingVisualCaptures") != []:
        raise AssertionError(f"artifact ledger reports missing visual captures: {ledger}")
    capture_status = ledger.get("visualCaptureStatus") or {}
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for capture in payload.get("captures") or []:
            if capture_status.get(capture) is not True:
                raise AssertionError(f"artifact ledger missing capture status for {capture}: {ledger}")
    if ledger.get("liveProofCount") != len(live_proofs):
        raise AssertionError(f"artifact ledger live proof count mismatch: {ledger}")

    manifest_paths = ledger.get("visualManifests") or []
    expected_manifest_paths = [str(path.relative_to(ROOT)) for path in manifests]
    if manifest_paths != expected_manifest_paths:
        raise AssertionError(f"artifact ledger visual manifest list mismatch: {ledger}")

    live_paths = ledger.get("liveProofs") or []
    expected_live_paths = [str(path.relative_to(ROOT)) for path in live_proofs]
    if live_paths != expected_live_paths:
        raise AssertionError(f"artifact ledger live proof list mismatch: {ledger}")
    live_status = ledger.get("liveProofStatus") or {}
    expected_live_ok = {
        str(path.relative_to(ROOT)): live_proof_ok(path)
        for path in live_proofs
    }
    for path in expected_live_paths:
        if live_status.get(path) is not expected_live_ok[path]:
            raise AssertionError(f"artifact ledger live proof status mismatch: {path} {ledger}")
    if ledger.get("liveProofOkCount") != sum(1 for ok in expected_live_ok.values() if ok):
        raise AssertionError(f"artifact ledger live ok count mismatch: {ledger}")
    expected_failed = sorted(path for path, ok in expected_live_ok.items() if not ok)
    if ledger.get("failedLiveProofCount") != len(expected_failed):
        raise AssertionError(f"artifact ledger failed live proof count mismatch expected {len(expected_failed)}: {ledger}")
    if ledger.get("failedLiveProofs") != expected_failed:
        raise AssertionError(f"artifact ledger failed live proof list mismatch expected {expected_failed}: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/artifact-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing artifact-ledger route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_artifact_ledger()
        print("artifact-ledger proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"artifact-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
