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
    "visual-surface-matrix-proof.py",
    "visual-coverage-proof.py",
    "view-inventory-proof.py",
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
        matrix = request("GET", "/qa/visual-surface-matrix")
        visual = request("GET", "/qa/visual-coverage")
        view = request("GET", "/qa/view-inventory")
        theme = request("GET", "/qa/theme-inventory")
        index = request("GET", "/qa/coverage-index", timeout=120.0)

        if matrix.get("ok") is not True:
            raise AssertionError(f"visual surface matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"visual surface matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"visual surface matrix proof-file parity mismatch: {matrix}")
        if matrix.get("proofOwnerFileParity") is not True:
            raise AssertionError(f"visual surface matrix owner parity mismatch: {matrix}")
        if matrix.get("surfaceCount") != visual.get("visualSurfaceCount"):
            raise AssertionError(f"visual surface matrix count mismatch: {matrix}")
        if matrix.get("surfaceParity") is not True:
            raise AssertionError(f"visual surface matrix parity mismatch: {matrix}")
        if matrix.get("manifestCount") != visual.get("manifestCount"):
            raise AssertionError(f"visual surface matrix manifest count mismatch: {matrix}")
        if matrix.get("viewStructCount") != view.get("viewStructCount"):
            raise AssertionError(f"visual surface matrix view count mismatch: {matrix}")
        if matrix.get("themeTokenCount") != theme.get("staticTokenCount"):
            raise AssertionError(f"visual surface matrix theme token count mismatch: {matrix}")

        rows = matrix.get("surfaceRows") or []
        if [row.get("surface") for row in rows] != visual.get("visualSurfaces"):
            raise AssertionError(f"visual surface matrix row order mismatch: {matrix}")
        for row in rows:
            surface = row.get("surface")
            proofs = row.get("proofs") or []
            manifests = row.get("manifests") or []
            view_groups = row.get("viewGroups") or []
            theme_groups = row.get("themeGroups") or []
            if proofs != (visual.get("visualSurfaceProofs") or {}).get(surface):
                raise AssertionError(f"{surface} proof map mismatch: {row}")
            assert_file_proofs_exist(proofs, surface or "surface")
            if row.get("proofOwnerExists") is not True:
                raise AssertionError(f"{surface} proof owner parity failed: {row}")
            if row.get("visualCoverageRoute") != "/qa/visual-coverage":
                raise AssertionError(f"{surface} visual route mismatch: {row}")
            if row.get("viewInventoryRoute") != "/qa/view-inventory":
                raise AssertionError(f"{surface} view inventory route mismatch: {row}")
            if row.get("themeInventoryRoute") != "/qa/theme-inventory":
                raise AssertionError(f"{surface} theme inventory route mismatch: {row}")
            if not manifests:
                raise AssertionError(f"{surface} has no manifest owners: {row}")
            if not view_groups:
                raise AssertionError(f"{surface} has no view group owners: {row}")
            if not theme_groups:
                raise AssertionError(f"{surface} has no theme group owners: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/visual-surface-matrix" not in state_routes:
            raise AssertionError(f"state routes missing visual surface matrix: {state_routes}")

        settings_visuals = (index.get("groups") or {}).get("settingsAndVisuals") or {}
        if settings_visuals.get("visualSurfaceMatrixCount") != matrix.get("surfaceCount"):
            raise AssertionError(f"coverage index visual surface matrix count mismatch: {index}")
        if settings_visuals.get("visualSurfaceMatrixProofOwnerFileParity") != matrix.get("proofOwnerFileParity"):
            raise AssertionError(f"coverage index visual surface matrix owner parity mismatch: {index}")
        if settings_visuals.get("visualSurfaceMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index visual surface matrix proof parity mismatch: {index}")
        if settings_visuals.get("visualSurfaceMatrixManifestCount") != matrix.get("manifestCount"):
            raise AssertionError(f"coverage index visual surface matrix manifest count mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/visual-surface-matrix",
            "visual-surface-matrix-proof.py",
            "visualSurfaceMatrixCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing visual surface matrix token {token}")

        print("visual-surface-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"visual-surface-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
