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
    "theme-token-matrix-proof.py",
    "theme-inventory-proof.py",
    "settings-surface-matrix-proof.py",
    "visual-surface-matrix-proof.py",
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
        matrix = request("GET", "/qa/theme-token-matrix")
        theme = request("GET", "/qa/theme-inventory")
        settings_surface = request("GET", "/qa/settings-surface-matrix")
        visual_surface = request("GET", "/qa/visual-surface-matrix")
        index = request("GET", "/qa/coverage-index", timeout=120.0)

        if matrix.get("ok") is not True:
            raise AssertionError(f"theme token matrix route failed: {matrix}")
        if matrix.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"theme token matrix proof list mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"theme token matrix proof-file parity mismatch: {matrix}")
        if matrix.get("fileCount") != theme.get("fileCount"):
            raise AssertionError(f"theme token matrix file count mismatch: {matrix}")
        if matrix.get("staticTokenCount") != theme.get("staticTokenCount"):
            raise AssertionError(f"theme token matrix static token count mismatch: {matrix}")
        if matrix.get("settingsSurfaceMatrixCount") != settings_surface.get("surfaceCount"):
            raise AssertionError(f"theme token matrix settings count mismatch: {matrix}")
        if matrix.get("visualSurfaceMatrixCount") != visual_surface.get("surfaceCount"):
            raise AssertionError(f"theme token matrix visual count mismatch: {matrix}")
        if matrix.get("policyParity") is not True:
            raise AssertionError(f"theme token matrix policy parity mismatch: {matrix}")

        rows = matrix.get("fileRows") or []
        if [row.get("file") for row in rows] != [row.get("file") for row in (theme.get("files") or [])]:
            raise AssertionError(f"theme token matrix row order mismatch: {matrix}")
        theme_by_file = {row.get("file"): row for row in (theme.get("files") or [])}
        for row in rows:
            file_name = row.get("file")
            source_row = theme_by_file.get(file_name) or {}
            if row.get("group") != source_row.get("group"):
                raise AssertionError(f"{file_name} group mismatch: {row}")
            if row.get("staticTokens") != source_row.get("staticTokens"):
                raise AssertionError(f"{file_name} static tokens mismatch: {row}")
            if row.get("staticTokenCount") != source_row.get("staticTokenCount"):
                raise AssertionError(f"{file_name} static token count mismatch: {row}")
            if row.get("proofOwner") != source_row.get("proofOwner"):
                raise AssertionError(f"{file_name} proof owner mismatch: {row}")
            assert_file_proofs_exist([row.get("proofOwner")], file_name or "theme file")
            if row.get("themeInventoryRoute") != "/qa/theme-inventory":
                raise AssertionError(f"{file_name} theme route mismatch: {row}")
            if row.get("settingsSurfaceMatrixRoute") != "/qa/settings-surface-matrix":
                raise AssertionError(f"{file_name} settings route mismatch: {row}")
            if row.get("visualSurfaceMatrixRoute") != "/qa/visual-surface-matrix":
                raise AssertionError(f"{file_name} visual route mismatch: {row}")
            if row.get("coverageIndexRoute") != "/qa/coverage-index":
                raise AssertionError(f"{file_name} coverage route mismatch: {row}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/theme-token-matrix" not in state_routes:
            raise AssertionError(f"state routes missing theme token matrix: {state_routes}")

        group = (index.get("groups") or {}).get("settingsAndVisuals") or {}
        if group.get("themeTokenMatrixFileCount") != matrix.get("fileCount"):
            raise AssertionError(f"coverage index theme token file count mismatch: {index}")
        if group.get("themeTokenMatrixStaticTokenCount") != matrix.get("staticTokenCount"):
            raise AssertionError(f"coverage index theme token static count mismatch: {index}")
        if group.get("themeTokenMatrixProofFileParity") != matrix.get("proofFileParity"):
            raise AssertionError(f"coverage index theme token proof parity mismatch: {index}")
        if group.get("themeTokenMatrixPolicyParity") != matrix.get("policyParity"):
            raise AssertionError(f"coverage index theme token policy parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in [
            "/qa/theme-token-matrix",
            "theme-token-matrix-proof.py",
            "themeTokenMatrixFileCount",
        ]:
            if token not in docs_text:
                raise AssertionError(f"docs missing theme token matrix token {token}")

        print("theme-token-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"theme-token-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
