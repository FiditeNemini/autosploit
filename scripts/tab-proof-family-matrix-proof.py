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
DOCS = [
    ROOT / "docs" / "app-system-review-2026-05-21.md",
    ROOT / "docs" / "app-flow-inventory-2026-05-21.md",
]

EXPECTED_FAMILIES = ["recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"]
EXPECTED_PROOFS = [
    "tab-proof-family-matrix-proof.py",
    "proof-ledger-proof.py",
    "tab-action-surface-matrix-proof.py",
    "tab-tool-function-flow-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 45.0):
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


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        matrix = request("GET", "/qa/tab-proof-family-matrix")
        proof_ledger = request("GET", "/qa/proof-ledger")
        tab_action_surface = request("GET", "/qa/tab-action-surface-matrix")
        tab_tool_flow = request("GET", "/qa/tab-tool-function-flow")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"tab proof family matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"tab proof family matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"tab proof family matrix proof-file parity mismatch: {matrix}")
        if matrix.get("familyProofFileParity") is not True:
            raise AssertionError(f"tab proof family matrix family proof parity mismatch: {matrix}")
        if matrix.get("familyParity") is not True:
            raise AssertionError(f"tab proof family matrix family parity mismatch: {matrix}")
        if matrix.get("familyCount") != len(EXPECTED_FAMILIES):
            raise AssertionError(f"tab proof family matrix family count mismatch: {matrix}")
        if matrix.get("proofLedgerTabProofFamilyCount") != proof_ledger.get("tabProofFamilyCount"):
            raise AssertionError(f"tab proof family matrix proof ledger family count mismatch: {matrix}")
        if matrix.get("tabActionSurfaceMatrixCount") != tab_action_surface.get("surfaceCount"):
            raise AssertionError(f"tab proof family matrix action surface count mismatch: {matrix}")
        if matrix.get("tabToolFunctionFlowCount") != tab_tool_flow.get("tabCount"):
            raise AssertionError(f"tab proof family matrix tab-flow count mismatch: {matrix}")

        rows = matrix.get("familyRows") or []
        if [row.get("family") for row in rows] != EXPECTED_FAMILIES:
            raise AssertionError(f"tab proof family matrix row order mismatch: {matrix}")
        ledger_families = proof_ledger.get("tabProofFamilies") or {}
        for row in rows:
            family = row.get("family") or ""
            ledger_payload = ledger_families.get(family) or {}
            proofs = row.get("proofs") or []
            if proofs != (ledger_payload.get("proofs") or []):
                raise AssertionError(f"tab proof family row proof list mismatch: {row}")
            if row.get("proofCount") != ledger_payload.get("count"):
                raise AssertionError(f"tab proof family row count mismatch: {row}")
            assert_file_proofs_exist(proofs, family)
            if row.get("proofFileParity") is not True:
                raise AssertionError(f"tab proof family row proof parity failed: {row}")
            if row.get("proofLedgerRoute") != "/qa/proof-ledger":
                raise AssertionError(f"tab proof family ledger route mismatch: {row}")
            if row.get("tabActionSurfaceMatrixRoute") != "/qa/tab-action-surface-matrix":
                raise AssertionError(f"tab proof family action-surface route mismatch: {row}")
            if row.get("tabToolFunctionFlowRoute") != "/qa/tab-tool-function-flow":
                raise AssertionError(f"tab proof family tab-flow route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/tab-proof-family-matrix" not in state_routes:
            raise AssertionError(f"state routes missing tab proof family matrix: {state_routes}")

        tabs_group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if tabs_group.get("tabProofFamilyMatrixCount") != matrix.get("familyCount"):
            raise AssertionError(f"coverage index tab proof family matrix count mismatch: {index}")
        if tabs_group.get("tabProofFamilyMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index tab proof family matrix proof parity mismatch: {index}")
        if tabs_group.get("tabProofFamilyMatrixFamilyProofFileParity") != matrix.get("familyProofFileParity"):
            raise AssertionError(f"coverage index tab proof family matrix family parity mismatch: {index}")
        if tabs_group.get("tabProofFamilyMatrixProofLedgerFamilyCount") != matrix.get("proofLedgerTabProofFamilyCount"):
            raise AssertionError(f"coverage index tab proof family matrix ledger family count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/tab-proof-family-matrix",
            "tab-proof-family-matrix-proof.py",
            "tabProofFamilyMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing tab proof family matrix token {token}")

        print("tab-proof-family-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tab-proof-family-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
