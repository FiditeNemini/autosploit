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
ARTIFACT = ROOT / "docs" / "live-proofs" / "2026-07-05-artifact-ledger-current.json"
KNOWN_FAILED_LIVE_PROOFS = [
    "docs/live-proofs/checkpoint-75-minimax-live.json",
]
EXPECTED_NON_PASSING_LIVE_PROOFS = {
    "docs/live-proofs/2026-07-04-live-batch-memory-preflight-blocked.json": "intentional memory preflight block before model load",
    "docs/live-proofs/2026-07-04-near-max-context-guard-refusal.json": "intentional near-max resource guard refusal",
    "docs/live-proofs/2026-07-04-near-max-context-runtime-attempt-summary.json": "partial near-max runtime attempt without final generation",
    "docs/live-proofs/2026-07-04-real-qwen-near-max-context-27b.json": "partial near-max long-context attempt without final generation",
    "docs/live-proofs/2026-07-05-long-context-200k-safety-refusal.json": "intentional above-safe-ceiling refusal",
    "docs/live-proofs/2026-07-05-long-context-224k-safety-refusal.json": "intentional above-safe-ceiling refusal",
    "docs/live-proofs/2026-07-05-real-qwen-long-context-200k-27b.json": "partial 200k long-context attempt stopped by memory guard",
    "docs/live-proofs/2026-07-05-real-qwen-long-context-224k-27b.json": "partial 224k long-context attempt stopped by memory guard",
    "docs/live-proofs/2026-07-05-release-app-computer-use-current-manual-sweep.json": "partial manual release UI sweep with notarization and loaded-model gates still open",
}
SUPERSEDED_FAILED_LIVE_PROOFS = {
    "docs/live-proofs/checkpoint-485-qwen-mxfp-live-current.json": "docs/live-proofs/checkpoint-486-qwen-mxfp-27b-pass.json",
    "docs/live-proofs/qwen27-mxfp4-mtp-live-cache-20260605.json": "docs/live-proofs/2026-07-04-qwen36-27b-mxfp8-mtp-live-batch.json",
    "docs/live-proofs/2026-07-04-qwen36-35b-ui-cve-tool-loop-partial.json": "docs/live-proofs/2026-07-04-qwen36-35b-ui-cve-tool-loop-after-loop-fix.json",
    "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on.json": "docs/live-proofs/2026-07-04-real-qwen-27b-reasoning-on-1024.json",
}


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


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_evidence() -> dict:
    output = subprocess.check_output(["ps", "-axo", "pid,rss,comm,args"], text=True)
    app_rows: list[str] = []
    engine_rows: list[str] = []
    engine_tokens = (
        "ExploitBotEngine/launch.py",
        "vmlx_engine.server",
        "mlx_server",
        "Qwen3.6",
        "MiniMax-M",
    )
    for line in output.splitlines():
        parts = line.split(None, 3)
        comm = parts[2] if len(parts) >= 3 else ""
        args = parts[3] if len(parts) >= 4 else ""
        if "ExploitBot.app/Contents/MacOS/ExploitBot" in line:
            app_rows.append(line.strip())
        shell_or_watcher = comm.endswith(("/zsh", "/bash", "/sh")) or "/.claude/" in args
        if not shell_or_watcher and any(token in line for token in engine_tokens):
            engine_rows.append(line.strip())
    return {
        "appRows": app_rows,
        "engineProcessRows": engine_rows,
    }


def expected_visual_manifests() -> list[Path]:
    return sorted((ROOT / "docs" / "visual-proofs").glob("checkpoint-*/manifest.json"))


def expected_live_proofs() -> list[Path]:
    return sorted((ROOT / "docs" / "live-proofs").glob("*.json"))


def live_proof_ok(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = payload.get("status")
    if payload.get("ok") is True or (isinstance(status, str) and status in {"passed", "PASS"}):
        return True
    verdict = payload.get("verdict") or {}
    if isinstance(verdict, dict) and any(str(value).startswith("FAIL") for value in verdict.values()):
        return False
    assertions = payload.get("assertions") or {}
    if isinstance(assertions, dict) and assertions:
        bool_values = [value for value in assertions.values() if isinstance(value, bool)]
        if bool_values:
            return all(value is True for value in bool_values)
    return False


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
    if ledger.get("visualManifestFileParity") is not True:
        raise AssertionError(f"artifact ledger visual manifest file parity mismatch: {ledger}")

    live_paths = ledger.get("liveProofs") or []
    expected_live_paths = [str(path.relative_to(ROOT)) for path in live_proofs]
    if live_paths != expected_live_paths:
        raise AssertionError(f"artifact ledger live proof list mismatch: {ledger}")
    if ledger.get("liveProofFileParity") is not True:
        raise AssertionError(f"artifact ledger live proof file parity mismatch: {ledger}")
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
    if ledger.get("knownFailedLiveProofs") != KNOWN_FAILED_LIVE_PROOFS:
        raise AssertionError(f"artifact ledger known failed live proof list mismatch: {ledger}")
    if ledger.get("knownFailedLiveProofCount") != len(KNOWN_FAILED_LIVE_PROOFS):
        raise AssertionError(f"artifact ledger known failed live proof count mismatch: {ledger}")
    if ledger.get("expectedNonPassingLiveProofs") != EXPECTED_NON_PASSING_LIVE_PROOFS:
        raise AssertionError(f"artifact ledger expected non-passing live proof map mismatch: {ledger}")
    if ledger.get("expectedNonPassingLiveProofCount") != len(EXPECTED_NON_PASSING_LIVE_PROOFS):
        raise AssertionError(f"artifact ledger expected non-passing live proof count mismatch: {ledger}")
    if ledger.get("supersededFailedLiveProofs") != SUPERSEDED_FAILED_LIVE_PROOFS:
        raise AssertionError(f"artifact ledger superseded failed live proof map mismatch: {ledger}")
    if ledger.get("supersededFailedLiveProofCount") != len(SUPERSEDED_FAILED_LIVE_PROOFS):
        raise AssertionError(f"artifact ledger superseded failed live proof count mismatch: {ledger}")
    replacement_status = ledger.get("supersededReplacementStatus") or {}
    for failed, replacement in SUPERSEDED_FAILED_LIVE_PROOFS.items():
        if replacement_status.get(failed) is not True:
            raise AssertionError(f"artifact ledger replacement is not passing for {failed} -> {replacement}: {ledger}")
    classified_failures = set(KNOWN_FAILED_LIVE_PROOFS).union(EXPECTED_NON_PASSING_LIVE_PROOFS.keys()).union(SUPERSEDED_FAILED_LIVE_PROOFS.keys())
    if ledger.get("currentFailedLiveProofs") != sorted(set(expected_failed).difference(classified_failures)):
        raise AssertionError(f"artifact ledger current failed live proof list mismatch: {ledger}")
    if ledger.get("currentFailedLiveProofCount") != len(set(expected_failed).difference(classified_failures)):
        raise AssertionError(f"artifact ledger current failed live proof count mismatch: {ledger}")
    if ledger.get("currentLiveProofFailureFree") is not True:
        raise AssertionError(f"artifact ledger should classify all current live proof failures: {ledger}")

    qa = state.get("qaCoverage") or {}
    if "/qa/artifact-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing artifact-ledger route contract: {qa}")

    model_inference_started = bool(state.get("engineRunning")) or bool(state.get("enginePort"))
    report = {
        "ok": True,
        "proofType": "artifact-ledger-current-live-route",
        "generatedAt": timestamp(),
        "sourceRoute": "/qa/artifact-ledger",
        "status": {
            "routeParity": "PASS",
            "visualManifestFileParity": "PASS" if ledger.get("visualManifestFileParity") is True else "FAIL",
            "liveProofFileParity": "PASS" if ledger.get("liveProofFileParity") is True else "FAIL",
            "currentLiveProofFailureFree": "PASS" if ledger.get("currentLiveProofFailureFree") is True else "FAIL",
            "modelInferenceStarted": "YES" if model_inference_started else "NO",
        },
        "visualManifestCount": ledger.get("visualManifestCount"),
        "visualCaptureCount": ledger.get("visualCaptureCount"),
        "liveProofCount": ledger.get("liveProofCount"),
        "liveProofOkCount": ledger.get("liveProofOkCount"),
        "failedLiveProofCount": ledger.get("failedLiveProofCount"),
        "failedLiveProofs": ledger.get("failedLiveProofs") or [],
        "knownFailedLiveProofs": ledger.get("knownFailedLiveProofs") or [],
        "expectedNonPassingLiveProofs": ledger.get("expectedNonPassingLiveProofs") or {},
        "supersededFailedLiveProofs": ledger.get("supersededFailedLiveProofs") or {},
        "currentFailedLiveProofCount": ledger.get("currentFailedLiveProofCount"),
        "currentFailedLiveProofs": ledger.get("currentFailedLiveProofs") or [],
        "liveProofs": ledger.get("liveProofs") or [],
        "liveProofStatus": ledger.get("liveProofStatus") or {},
        "stateEvidence": {
            "engineRunning": bool(state.get("engineRunning")),
            "enginePort": state.get("enginePort"),
            "healthStatus": state.get("healthStatus"),
        },
        "processEvidence": process_evidence(),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        print(f"artifact-ledger proof passed and wrote {ARTIFACT}")
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
