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
    "artifact-manifest-matrix-proof.py",
    "artifact-ledger-proof.py",
    "visual-surface-matrix-proof.py",
    "runtime-coverage-proof.py",
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


def expected_manifest_rows(artifact_ledger: dict) -> list[str]:
    return artifact_ledger.get("visualManifests") or []


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
        matrix = request("GET", "/qa/artifact-manifest-matrix")
        artifact = request("GET", "/qa/artifact-ledger")
        visual_surface = request("GET", "/qa/visual-surface-matrix")
        runtime = request("GET", "/qa/runtime-coverage")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"artifact manifest matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"artifact manifest matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"artifact manifest matrix proof-file parity mismatch: {matrix}")
        if matrix.get("manifestFileParity") is not True:
            raise AssertionError(f"artifact manifest matrix manifest parity mismatch: {matrix}")
        if matrix.get("captureFileParity") is not True:
            raise AssertionError(f"artifact manifest matrix capture parity mismatch: {matrix}")
        if matrix.get("manifestCount") != artifact.get("visualManifestCount"):
            raise AssertionError(f"artifact manifest matrix count mismatch: {matrix}")
        if matrix.get("visualSurfaceMatrixCount") != visual_surface.get("surfaceCount"):
            raise AssertionError(f"artifact manifest matrix visual surface count mismatch: {matrix}")
        if matrix.get("runtimeLiveProofArtifactCount") != runtime.get("liveProofArtifactCount"):
            raise AssertionError(f"artifact manifest matrix runtime artifact count mismatch: {matrix}")

        rows = matrix.get("manifestRows") or []
        if [row.get("manifest") for row in rows] != expected_manifest_rows(artifact):
            raise AssertionError(f"artifact manifest matrix row order mismatch: {matrix}")
        for row in rows:
            proofs = row.get("proofs") or []
            if not proofs:
                raise AssertionError(f"artifact manifest row has no proof owners: {row}")
            assert_file_proofs_exist(proofs, row.get("manifest") or "manifest")
            if row.get("manifestExists") is not True:
                raise AssertionError(f"artifact manifest row missing manifest: {row}")
            if row.get("capturesExist") is not True:
                raise AssertionError(f"artifact manifest row missing captures: {row}")
            if row.get("artifactLedgerRoute") != "/qa/artifact-ledger":
                raise AssertionError(f"artifact manifest ledger route mismatch: {row}")
            if row.get("visualSurfaceMatrixRoute") != "/qa/visual-surface-matrix":
                raise AssertionError(f"artifact manifest visual route mismatch: {row}")
            if row.get("runtimeCoverageRoute") != "/qa/runtime-coverage":
                raise AssertionError(f"artifact manifest runtime route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/artifact-manifest-matrix" not in state_routes:
            raise AssertionError(f"state routes missing artifact manifest matrix: {state_routes}")

        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("artifactManifestMatrixCount") != matrix.get("manifestCount"):
            raise AssertionError(f"coverage index artifact manifest matrix count mismatch: {index}")
        if app_group.get("artifactManifestMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index artifact manifest matrix proof parity mismatch: {index}")
        if app_group.get("artifactManifestMatrixManifestFileParity") != matrix.get("manifestFileParity"):
            raise AssertionError(f"coverage index artifact manifest matrix manifest parity mismatch: {index}")
        if app_group.get("artifactManifestMatrixCaptureFileParity") != matrix.get("captureFileParity"):
            raise AssertionError(f"coverage index artifact manifest matrix capture parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/artifact-manifest-matrix",
            "artifact-manifest-matrix-proof.py",
            "artifactManifestMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing artifact manifest matrix token {token}")

        print("artifact-manifest-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"artifact-manifest-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
