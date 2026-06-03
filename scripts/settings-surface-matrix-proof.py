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
    "settings-surface-matrix-proof.py",
    "settings-coverage-proof.py",
    "visual-surface-matrix-proof.py",
    "theme-inventory-proof.py",
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
        matrix = request("GET", "/qa/settings-surface-matrix")
        settings = request("GET", "/qa/settings-coverage")
        visual_surface = request("GET", "/qa/visual-surface-matrix")
        theme = request("GET", "/qa/theme-inventory")
        index = request("GET", "/qa/coverage-index")

        if matrix.get("ok") is not True:
            raise AssertionError(f"settings surface matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"settings surface matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"settings surface matrix proof parity mismatch: {matrix}")
        if matrix.get("surfaceProofFileParity") is not True:
            raise AssertionError(f"settings surface matrix surface proof parity mismatch: {matrix}")
        if matrix.get("surfaceCount") != settings.get("settingsSurfaceCount"):
            raise AssertionError(f"settings surface matrix surface count mismatch: {matrix}")
        if matrix.get("categoryCount") != settings.get("categoryCount"):
            raise AssertionError(f"settings surface matrix category count mismatch: {matrix}")
        if matrix.get("visualSurfaceMatrixCount") != visual_surface.get("surfaceCount"):
            raise AssertionError(f"settings surface matrix visual surface count mismatch: {matrix}")
        if matrix.get("themeInventoryFileCount") != theme.get("fileCount"):
            raise AssertionError(f"settings surface matrix theme file count mismatch: {matrix}")

        rows = matrix.get("surfaceRows") or []
        if [row.get("surface") for row in rows] != (settings.get("settingsSurfaces") or []):
            raise AssertionError(f"settings surface matrix row order mismatch: {matrix}")
        proof_map = settings.get("settingsSurfaceProofs") or {}
        for row in rows:
            surface = row.get("surface")
            if row.get("proofs") != proof_map.get(surface):
                raise AssertionError(f"settings surface matrix proof owner mismatch: {row}")
            assert_file_proofs_exist(row.get("proofs") or [], surface or "settings surface")
            if row.get("settingsCoverageRoute") != "/qa/settings-coverage":
                raise AssertionError(f"settings surface row settings route mismatch: {row}")
            if row.get("visualSurfaceMatrixRoute") != "/qa/visual-surface-matrix":
                raise AssertionError(f"settings surface row visual route mismatch: {row}")
            if row.get("themeInventoryRoute") != "/qa/theme-inventory":
                raise AssertionError(f"settings surface row theme route mismatch: {row}")
            if row.get("coverageIndexRoute") != "/qa/coverage-index":
                raise AssertionError(f"settings surface row coverage route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/settings-surface-matrix" not in state_routes:
            raise AssertionError(f"state routes missing settings surface matrix: {state_routes}")

        group = (index.get("groups") or {}).get("settingsAndVisuals") or {}
        if group.get("settingsSurfaceMatrixCount") != matrix.get("surfaceCount"):
            raise AssertionError(f"coverage index settings surface matrix count mismatch: {index}")
        if group.get("settingsSurfaceMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index settings surface matrix proof parity mismatch: {index}")
        if group.get("settingsSurfaceMatrixSurfaceProofFileParity") != matrix.get("surfaceProofFileParity"):
            raise AssertionError(f"coverage index settings surface matrix surface proof parity mismatch: {index}")
        if group.get("settingsSurfaceMatrixThemeFileCount") != matrix.get("themeInventoryFileCount"):
            raise AssertionError(f"coverage index settings surface matrix theme count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/settings-surface-matrix",
            "settings-surface-matrix-proof.py",
            "settingsSurfaceMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing settings surface matrix token {token}")

        print("settings-surface-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"settings-surface-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
