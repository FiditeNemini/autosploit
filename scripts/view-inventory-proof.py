#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
SOURCE_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot"
VIEW_ROOTS = [
    SOURCE_ROOT / "App",
    SOURCE_ROOT / "Views",
]

EXPECTED_GROUPS = [
    "appShell",
    "chat",
    "tabs",
    "settings",
    "navigation",
    "overlaysAndPanels",
]

EXPECTED_MAIN_TAB_VIEWS = {
    "recon": "ReconTabView",
    "web": "WebTabView",
    "network": "NetworkTabView",
    "creds": "CredsTabView",
    "exploit": "ExploitTabView",
    "post": "PostExploitTabView",
    "osint": "OSINTTabView",
    "report": "ReportTabView",
    "stash": "StashTabView",
}

EXPECTED_PROOFS = [
    "view-inventory-proof.py",
    "app-qa-matrix-smoke-proof.py",
    "coverage-index-proof.py",
    "visual-tab-proof.py",
    "visual-chat-interaction-proof.py",
    "visual-settings-proof.py",
    "visual-report-export-proof.py",
    "visual-osint-artifact-actions-proof.py",
    "visual-unsupported-model-proof.py",
    "visual-cve-settings-status-proof.py",
    "visual-tool-settings-status-proof.py",
    "tab-action-coverage-proof.py",
    "subtab-coverage-proof.py",
    "settings-coverage-proof.py",
]


def view_files() -> list[Path]:
    files: list[Path] = []
    for root in VIEW_ROOTS:
        files.extend(sorted(root.rglob("*.swift")))
    return sorted(files)


def view_structs() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in view_files():
        text = path.read_text(encoding="utf-8")
        for name in re.findall(r"^(?:private\s+)?struct\s+(\w+)\s*:\s*View\b", text, re.MULTILINE):
            rel = str(path.relative_to(ROOT))
            rows.append(
                {
                    "name": name,
                    "file": rel,
                    "group": group_for(path, name),
                    "proofOwner": proof_for(path, name),
                }
            )
    return rows


def group_for(path: Path, name: str) -> str:
    rel = str(path.relative_to(SOURCE_ROOT))
    if rel.startswith("App/") or name in {"ContentView"}:
        return "appShell"
    if "/Chat/" in rel:
        return "chat"
    if "/Tabs/" in rel:
        return "tabs"
    if "/Settings/" in rel:
        return "settings"
    if name in {"TabBarView", "TabButton", "TabActivityIndicator", "ToolbarButton", "PhaseIndicatorView", "SidebarView", "OpItemView"}:
        return "navigation"
    return "overlaysAndPanels"


def proof_for(path: Path, name: str) -> str:
    rel = str(path.relative_to(SOURCE_ROOT))
    if "/Tabs/" in rel or name in {"TabBarView", "TabButton", "TabActivityIndicator", "ToolbarButton"}:
        return "visual-tab-proof.py"
    if "/Chat/" in rel:
        return "visual-chat-interaction-proof.py"
    if "/Settings/" in rel:
        return "visual-settings-proof.py"
    if name == "FindingWizardView":
        return "finding-wizard-submit-proof.py"
    if name == "TerminalPanelView":
        return "window-overlay-actions-proof.py"
    return "app-qa-matrix-smoke-proof.py"


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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        files = [str(path.relative_to(ROOT)) for path in view_files()]
        structs = view_structs()
        payload = request("GET", "/qa/view-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"view inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot":
            raise AssertionError(f"view inventory source root mismatch: {payload}")
        if payload.get("viewFiles") != files:
            raise AssertionError(f"view inventory file list mismatch: {payload}")
        if payload.get("viewFileCount") != len(files):
            raise AssertionError(f"view inventory file count mismatch: {payload}")
        if payload.get("viewStructs") != structs:
            raise AssertionError(f"view inventory struct list mismatch: {payload}")
        if payload.get("viewStructCount") != len(structs):
            raise AssertionError(f"view inventory struct count mismatch: {payload}")
        if any(not item.get("proofOwner") for item in payload.get("viewStructs") or []):
            raise AssertionError(f"view inventory missing proof owner: {payload}")
        if any(not item.get("group") for item in payload.get("viewStructs") or []):
            raise AssertionError(f"view inventory missing group: {payload}")

        if payload.get("mainTabViews") != EXPECTED_MAIN_TAB_VIEWS:
            raise AssertionError(f"view inventory main tab map mismatch: {payload}")
        if payload.get("mainTabViewCount") != len(EXPECTED_MAIN_TAB_VIEWS):
            raise AssertionError(f"view inventory main tab count mismatch: {payload}")
        if payload.get("mainTabParity") is not True:
            raise AssertionError(f"view inventory main tab parity mismatch: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"view inventory group list mismatch: {payload}")
        group_counts = payload.get("groupCounts") or {}
        if set(group_counts) != set(EXPECTED_GROUPS):
            raise AssertionError(f"view inventory group count keys mismatch: {payload}")
        if sum(group_counts.values()) != len(structs):
            raise AssertionError(f"view inventory group counts do not cover structs: {payload}")
        expected_counts = dict(Counter(item["group"] for item in structs))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if group_counts != expected_counts:
            raise AssertionError(f"view inventory group counts mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/view-inventory" not in state_routes:
            raise AssertionError(f"state route list missing view inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        app_group = (index.get("groups") or {}).get("appState") or {}
        if app_group.get("viewInventoryStructCount") != payload.get("viewStructCount"):
            raise AssertionError(f"coverage index view inventory struct count mismatch: {index}")
        if app_group.get("viewInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index view inventory group count mismatch: {index}")
        if app_group.get("viewInventoryMainTabViews") != payload.get("mainTabViews"):
            raise AssertionError(f"coverage index view inventory tab map mismatch: {index}")
        if app_group.get("viewInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index view inventory proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"view inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"view inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"view inventory proof-file parity mismatch: {payload}")
        missing_files = sorted(name for name in EXPECTED_PROOFS if not (ROOT / "scripts" / name).is_file())
        if missing_files:
            raise AssertionError(f"view inventory names missing proof files: {missing_files}")

        print("view-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"view-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
