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

EXPECTED_SURFACES = ["agent", "chat", "context", "release", "runtime", "settings", "tabs", "tools", "visual"]
EXPECTED_PROOFS = [
    "proof-category-matrix-proof.py",
    "proof-ledger-proof.py",
    "proof-suite-inventory-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


def request(method: str, path: str, body: str | None = None, timeout: float = 15.0):
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
        matrix = request("GET", "/qa/proof-category-matrix")
        proof_ledger = request("GET", "/qa/proof-ledger")
        proof_suite = request("GET", "/qa/proof-suite-inventory")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"proof category matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"proof category matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"proof category matrix proof-file parity mismatch: {matrix}")
        if matrix.get("categoryProofFileParity") is not True:
            raise AssertionError(f"proof category matrix category proof parity mismatch: {matrix}")
        if matrix.get("categorySurfaces") != EXPECTED_SURFACES:
            raise AssertionError(f"proof category matrix category surfaces mismatch: {matrix}")
        if matrix.get("categoryCount") != len(EXPECTED_SURFACES):
            raise AssertionError(f"proof category matrix category count mismatch: {matrix}")
        if matrix.get("proofLedgerCount") != proof_ledger.get("proofCount"):
            raise AssertionError(f"proof category matrix proof ledger count mismatch: {matrix}")
        if matrix.get("proofSuiteInventoryFileCount") != proof_suite.get("fileCount"):
            raise AssertionError(f"proof category matrix proof suite count mismatch: {matrix}")

        rows = matrix.get("categoryRows") or []
        if [row.get("category") for row in rows] != EXPECTED_SURFACES:
            raise AssertionError(f"proof category matrix row order mismatch: {matrix}")
        ledger_categories = proof_ledger.get("categories") or {}
        for row in rows:
            category = row.get("category") or ""
            ledger_payload = ledger_categories.get(category) or {}
            proofs = row.get("proofs") or []
            if proofs != (ledger_payload.get("proofs") or []):
                raise AssertionError(f"proof category row proof list mismatch: {row}")
            if row.get("proofCount") != ledger_payload.get("count"):
                raise AssertionError(f"proof category row count mismatch: {row}")
            assert_file_proofs_exist(proofs, category)
            if row.get("proofFileParity") is not True:
                raise AssertionError(f"proof category row file parity failed: {row}")
            if row.get("proofLedgerRoute") != "/qa/proof-ledger":
                raise AssertionError(f"proof category ledger route mismatch: {row}")
            if row.get("proofSuiteInventoryRoute") != "/qa/proof-suite-inventory":
                raise AssertionError(f"proof category suite route mismatch: {row}")
            if row.get("coverageIndexRoute") != "/qa/coverage-index":
                raise AssertionError(f"proof category coverage-index route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/proof-category-matrix" not in state_routes:
            raise AssertionError(f"state routes missing proof category matrix: {state_routes}")

        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("proofCategoryMatrixCount") != matrix.get("categoryCount"):
            raise AssertionError(f"coverage index proof category matrix count mismatch: {index}")
        if app_group.get("proofCategoryMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index proof category matrix proof parity mismatch: {index}")
        if app_group.get("proofCategoryMatrixCategoryProofFileParity") != matrix.get("categoryProofFileParity"):
            raise AssertionError(f"coverage index proof category matrix category parity mismatch: {index}")
        if app_group.get("proofCategoryMatrixProofLedgerCount") != matrix.get("proofLedgerCount"):
            raise AssertionError(f"coverage index proof category matrix ledger count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/proof-category-matrix",
            "proof-category-matrix-proof.py",
            "proofCategoryMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing proof category matrix token {token}")

        print("proof-category-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"proof-category-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
