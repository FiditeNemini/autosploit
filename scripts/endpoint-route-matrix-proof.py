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

EXPECTED_PROOFS = [
    "endpoint-route-matrix-proof.py",
    "endpoint-inventory-proof.py",
    "action-state-inventory-proof.py",
    "tab-action-coverage-proof.py",
    "coverage-index-proof.py",
    "app-qa-matrix-smoke-proof.py",
]


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


def assert_file_proofs_exist(proofs: list[str], label: str) -> None:
    missing = [proof for proof in proofs if not (ROOT / "scripts" / proof).is_file()]
    if missing:
        raise AssertionError(f"{label} names missing proof files: {missing}")


def expected_rows(endpoint_inventory: dict) -> list[tuple[str, str]]:
    return [
        (item.get("method") or "", item.get("path") or "")
        for item in endpoint_inventory.get("routes") or []
    ]


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
        matrix = request("GET", "/qa/endpoint-route-matrix")
        endpoint_inventory = request("GET", "/qa/endpoint-inventory")
        action_state = request("GET", "/qa/action-state-inventory")
        tab_action = request("GET", "/qa/tab-action-coverage")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"endpoint route matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"endpoint route matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"endpoint route matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"endpoint route matrix owner parity mismatch: {matrix}")
        if matrix.get("routeCount") != endpoint_inventory.get("routeCount"):
            raise AssertionError(f"endpoint route matrix route count mismatch: {matrix}")
        if matrix.get("rowParity") is not True:
            raise AssertionError(f"endpoint route matrix row parity mismatch: {matrix}")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if matrix.get("stateRouteCount") != len(state_routes):
            raise AssertionError(f"endpoint route matrix state route count mismatch: {matrix}")
        if matrix.get("actionStateInventoryCount") != action_state.get("actionStateCount"):
            raise AssertionError(f"endpoint route matrix action-state count mismatch: {matrix}")
        if matrix.get("tabActionRouteCount") != len(tab_action.get("routes") or []):
            raise AssertionError(f"endpoint route matrix tab-action route count mismatch: {matrix}")

        rows = matrix.get("routeRows") or []
        if [(row.get("method") or "", row.get("path") or "") for row in rows] != expected_rows(endpoint_inventory):
            raise AssertionError(f"endpoint route matrix row order mismatch: {matrix}")
        for row in rows:
            proofs = row.get("proofs") or []
            if not proofs:
                raise AssertionError(f"endpoint route row has no proof owners: {row}")
            assert_file_proofs_exist(proofs, row.get("path") or "endpoint-route")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"endpoint route proof owner parity failed: {row}")
            if row.get("endpointInventoryRoute") != "/qa/endpoint-inventory":
                raise AssertionError(f"endpoint route inventory route mismatch: {row}")
            if row.get("actionStateInventoryRoute") != "/qa/action-state-inventory":
                raise AssertionError(f"endpoint route action-state route mismatch: {row}")
            if row.get("coverageIndexRoute") != "/qa/coverage-index":
                raise AssertionError(f"endpoint route coverage-index route mismatch: {row}")
            if not row.get("group"):
                raise AssertionError(f"endpoint route group missing: {row}")

        if "/qa/endpoint-route-matrix" not in state_routes:
            raise AssertionError(f"state routes missing endpoint route matrix: {state_routes}")

        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("endpointRouteMatrixCount") != matrix.get("routeCount"):
            raise AssertionError(f"coverage index endpoint route matrix count mismatch: {index}")
        if app_group.get("endpointRouteMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index endpoint route matrix owner parity mismatch: {index}")
        if app_group.get("endpointRouteMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index endpoint route matrix proof parity mismatch: {index}")
        if app_group.get("endpointRouteMatrixStateRouteCount") != matrix.get("stateRouteCount"):
            raise AssertionError(f"coverage index endpoint route matrix state route count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/endpoint-route-matrix",
            "endpoint-route-matrix-proof.py",
            "endpointRouteMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing endpoint route matrix token {token}")

        print("endpoint-route-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"endpoint-route-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
