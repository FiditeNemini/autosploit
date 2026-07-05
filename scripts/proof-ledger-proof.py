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
ARTIFACT = ROOT / "docs" / "live-proofs" / "2026-07-05-proof-ledger-current.json"

SPECIAL_PROOFS = {
    "live-turn-harness.py",
    "verify-live-models.py",
    "prove-parser-api.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
    "prove-live-continuous-batching.py",
    "prove-live-minimax-continuous-batching.py",
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


def expected_proofs() -> list[str]:
    names = []
    for path in (ROOT / "scripts").glob("*.py"):
        if path.name.endswith("-proof.py") or path.name in SPECIAL_PROOFS:
            names.append(path.name)
    return sorted(names)


def assert_proof_ledger() -> None:
    state = request("GET", "/state")
    ledger = request("GET", "/qa/proof-ledger")
    expected = expected_proofs()

    if ledger.get("ok") is not True:
        raise AssertionError(f"/qa/proof-ledger failed: {ledger}")
    if ledger.get("proofCount") != len(expected):
        raise AssertionError(f"proof ledger count mismatch expected {len(expected)}: {ledger}")
    proofs = ledger.get("proofs") or []
    if proofs != expected:
        missing = sorted(set(expected).difference(proofs))
        extra = sorted(set(proofs).difference(expected))
        raise AssertionError(f"proof ledger mismatch missing={missing} extra={extra}")
    missing_files = sorted(name for name in proofs if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"proof ledger names non-existent proof files: {missing_files}")
    if ledger.get("proofFileParity") is not True:
        raise AssertionError(f"proof ledger proof-file parity mismatch: {ledger}")
    categories = ledger.get("categories") or {}
    category_surfaces = sorted(("agent", "chat", "context", "release", "runtime", "settings", "tabs", "tools", "visual"))
    if ledger.get("categorySurfaces") != category_surfaces:
        raise AssertionError(f"proof ledger category surfaces mismatch: {ledger}")
    if ledger.get("categorySurfaceCount") != len(category_surfaces):
        raise AssertionError(f"proof ledger category surface count mismatch: {ledger}")
    category_counts = {
        name: category.get("count")
        for name, category in categories.items()
    }
    if ledger.get("categoryCounts") != category_counts:
        raise AssertionError(f"proof ledger category counts mismatch: {ledger}")
    if ledger.get("categoryOtherCount") != category_counts.get("other"):
        raise AssertionError(f"proof ledger other category count mismatch: {ledger}")
    category_total = sum((category.get("count") or 0) for category in categories.values())
    if ledger.get("categoryTotalCount") != category_total:
        raise AssertionError(f"proof ledger category total count mismatch: {ledger}")
    if ledger.get("categoryParity") is not True:
        raise AssertionError(f"proof ledger category parity mismatch: {ledger}")
    for key in category_surfaces:
        if (categories.get(key) or {}).get("count", 0) <= 0:
            raise AssertionError(f"proof ledger missing category {key}: {ledger}")
    if (categories.get("visual") or {}).get("count", 0) < 20:
        raise AssertionError(f"proof ledger visual category too small: {ledger}")
    if (categories.get("runtime") or {}).get("count", 0) < 8:
        raise AssertionError(f"proof ledger runtime category too small: {ledger}")
    if "release-readiness-proof.py" not in (categories.get("release") or {}).get("proofs", []):
        raise AssertionError(f"proof ledger missing release readiness proof category: {ledger}")
    tab_owned_proofs = {
        "recon-action-status-proof.py",
        "web-direct-actions-proof.py",
        "network-protocol-action-proof.py",
        "creds-action-results-proof.py",
        "exploit-action-differentiation-proof.py",
        "post-attribution-proof.py",
        "osint-artifact-actions-proof.py",
        "report-generate-action-proof.py",
        "stash-actions-proof.py",
    }
    tabs_proofs = set((categories.get("tabs") or {}).get("proofs") or [])
    missing_tab_owned = sorted(tab_owned_proofs.difference(tabs_proofs))
    if missing_tab_owned:
        raise AssertionError(f"proof ledger tab-owned action proofs categorized outside tabs: {missing_tab_owned}")
    if ledger.get("categoryOtherCount", 99) > 30:
        raise AssertionError(f"proof ledger other category still too broad: {ledger}")
    expected_tab_families = {
        "recon": {"recon-subtab-state-proof.py", "recon-action-status-proof.py", "recon-copy-actions-proof.py"},
        "web": {"web-subtab-state-proof.py", "web-direct-actions-proof.py", "web-verify-action-proof.py"},
        "network": {"network-subtab-state-proof.py", "network-protocol-action-proof.py", "network-copy-actions-proof.py"},
        "creds": {"creds-subtab-state-proof.py", "creds-action-results-proof.py", "creds-copy-actions-proof.py"},
        "exploit": {"exploit-subtab-state-proof.py", "exploit-action-differentiation-proof.py", "exploit-copy-actions-proof.py"},
        "post": {"post-subtab-state-proof.py", "post-attribution-proof.py", "post-copy-actions-proof.py"},
        "supplyChain": {"supply-chain-cve-ui-proof.py"},
        "osint": {"osint-subtab-state-proof.py", "osint-artifact-actions-proof.py", "osint-copy-actions-proof.py"},
        "report": {"report-subtab-state-proof.py", "report-generate-action-proof.py", "report-export-proof.py"},
        "stash": {"stash-actions-proof.py", "stash-row-context-actions-proof.py", "stash-send-chat-control-proof.py"},
    }
    tab_families = ledger.get("tabProofFamilies") or {}
    if sorted(tab_families) != sorted(expected_tab_families):
        raise AssertionError(f"proof ledger tab family keys mismatch: {ledger}")
    if ledger.get("tabProofFamilyCount") != len(expected_tab_families):
        raise AssertionError(f"proof ledger tab family count mismatch: {ledger}")
    if ledger.get("tabProofFamilyParity") is not True:
        raise AssertionError(f"proof ledger tab family parity mismatch: {ledger}")
    if ledger.get("tabProofFamilyFileParity") is not True:
        raise AssertionError(f"proof ledger tab family file parity mismatch: {ledger}")
    for family, required in expected_tab_families.items():
        payload = tab_families.get(family) or {}
        proofs_for_family = set(payload.get("proofs") or [])
        missing_family = sorted(required.difference(proofs_for_family))
        if missing_family:
            raise AssertionError(f"proof ledger tab family {family} missing proofs {missing_family}: {payload}")
        if payload.get("count") != len(payload.get("proofs") or []):
            raise AssertionError(f"proof ledger tab family count mismatch {family}: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"proof ledger tab family file parity mismatch {family}: {payload}")

    qa = state.get("qaCoverage") or {}
    if "/qa/proof-ledger" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing proof-ledger route contract: {qa}")

    model_inference_started = bool(state.get("engineRunning")) or bool(state.get("enginePort"))
    report = {
        "ok": True,
        "proofType": "proof-ledger-current-live-route",
        "generatedAt": timestamp(),
        "sourceRoute": "/qa/proof-ledger",
        "status": {
            "routeParity": "PASS",
            "proofFileParity": "PASS" if ledger.get("proofFileParity") is True else "FAIL",
            "categoryParity": "PASS" if ledger.get("categoryParity") is True else "FAIL",
            "tabProofFamilyParity": "PASS" if ledger.get("tabProofFamilyParity") is True else "FAIL",
            "modelInferenceStarted": "YES" if model_inference_started else "NO",
        },
        "proofCount": ledger.get("proofCount"),
        "categorySurfaces": ledger.get("categorySurfaces") or [],
        "categoryCounts": ledger.get("categoryCounts") or {},
        "categoryOtherCount": ledger.get("categoryOtherCount"),
        "tabProofFamilyCount": ledger.get("tabProofFamilyCount"),
        "tabProofFamilies": ledger.get("tabProofFamilies") or {},
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
        assert_proof_ledger()
        print(f"proof-ledger proof passed and wrote {ARTIFACT}")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"proof-ledger proof failed: {exc}", flush=True)
        raise SystemExit(1)
