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

EXPECTED_TABS = ["recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"]
EXPECTED_VIEWS = {
    "recon": "ReconTabView",
    "web": "WebTabView",
    "network": "NetworkTabView",
    "creds": "CredsTabView",
    "exploit": "ExploitTabView",
    "post": "PostExploitTabView",
    "supplyChain": "SupplyChainTabView",
    "osint": "OSINTTabView",
    "report": "ReportTabView",
    "stash": "StashTabView",
}
EXPECTED_ACTION_SURFACES = {
    tab: f"{tab}Actions" for tab in EXPECTED_TABS
}
EXPECTED_ACTION_SURFACES["creds"] = "credsActions"
EXPECTED_ACTION_SURFACES["osint"] = "osintActions"

EXPECTED_PROOFS = [
    "tab-tool-function-flow-proof.py",
    "tab-action-coverage-proof.py",
    "tool-flow-coverage-proof.py",
    "function-flow-inventory-proof.py",
    "agent-loop-coverage-proof.py",
    "view-inventory-proof.py",
    "subtab-coverage-proof.py",
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
        flow = request("GET", "/qa/tab-tool-function-flow")
        tool_registry = request("GET", "/qa/tool-coverage")
        tab_actions = request("GET", "/qa/tab-action-coverage")
        subtabs = request("GET", "/qa/subtab-coverage")
        views = request("GET", "/qa/view-inventory")
        functions = request("GET", "/qa/function-flow-inventory")
        agent_loop = request("GET", "/qa/agent-loop-coverage")
        index = request("GET", "/qa/coverage-index")

        if flow.get("ok") is not True:
            raise AssertionError(f"tab-tool-function flow route failed: {flow}")
        if flow.get("tabs") != EXPECTED_TABS:
            raise AssertionError(f"tab-tool-function tab list mismatch: {flow}")
        if flow.get("tabCount") != len(EXPECTED_TABS):
            raise AssertionError(f"tab-tool-function tab count mismatch: {flow}")
        if flow.get("tabParity") is not True:
            raise AssertionError(f"tab-tool-function tab parity mismatch: {flow}")
        if flow.get("proofs") != EXPECTED_PROOFS:
            raise AssertionError(f"tab-tool-function proof list mismatch: {flow}")
        if flow.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"tab-tool-function proof count mismatch: {flow}")
        if flow.get("proofFileParity") is not True:
            raise AssertionError(f"tab-tool-function proof-file parity mismatch: {flow}")

        rows = flow.get("flows") or []
        if len(rows) != len(EXPECTED_TABS):
            raise AssertionError(f"tab-tool-function row count mismatch: {flow}")
        rows_by_tab = {row.get("tab"): row for row in rows}
        if list(rows_by_tab) != EXPECTED_TABS:
            raise AssertionError(f"tab-tool-function row order mismatch: {flow}")

        tab_tool_map = tool_registry.get("tabToolMap") or {}
        action_surface_proofs = tab_actions.get("tabActionSurfaceProofs") or {}
        subtab_map = subtabs.get("tabs") or {}
        view_map = views.get("mainTabViews") or {}
        loop_phases = agent_loop.get("loopPhases") or []

        for tab in EXPECTED_TABS:
            row = rows_by_tab[tab]
            if row.get("view") != EXPECTED_VIEWS[tab]:
                raise AssertionError(f"{tab} view mismatch: {row}")
            if row.get("tools") != (tab_tool_map.get(tab) or []):
                raise AssertionError(f"{tab} tool list mismatch: {row}")
            if row.get("toolCount") != len(tab_tool_map.get(tab) or []):
                raise AssertionError(f"{tab} tool count mismatch: {row}")
            if row.get("actionSurface") != EXPECTED_ACTION_SURFACES[tab]:
                raise AssertionError(f"{tab} action surface mismatch: {row}")
            if row.get("actionProofs") != action_surface_proofs.get(EXPECTED_ACTION_SURFACES[tab]):
                raise AssertionError(f"{tab} action proof mismatch: {row}")
            expected_subtab = subtab_map.get(tab)
            if tab == "stash":
                if row.get("hasSubtabs") is not False or row.get("subtabCount") != 0:
                    raise AssertionError(f"stash should be explicit no-subtab flow: {row}")
            else:
                if row.get("hasSubtabs") is not True:
                    raise AssertionError(f"{tab} missing subtab flow: {row}")
                if row.get("subtabCount") != expected_subtab.get("count"):
                    raise AssertionError(f"{tab} subtab count mismatch: {row}")
                if row.get("subtabProof") != expected_subtab.get("proof"):
                    raise AssertionError(f"{tab} subtab proof mismatch: {row}")
            if row.get("agentLoopPhaseCount") != len(loop_phases):
                raise AssertionError(f"{tab} agent loop phase count mismatch: {row}")
            if row.get("agentLoopPhases") != loop_phases:
                raise AssertionError(f"{tab} agent loop phase list mismatch: {row}")
            if row.get("functionFlowRoute") != "/qa/function-flow-inventory":
                raise AssertionError(f"{tab} missing function-flow route: {row}")
            if row.get("functionFlowCount") != functions.get("functionCount"):
                raise AssertionError(f"{tab} function-flow count mismatch: {row}")

        if flow.get("viewMap") != view_map:
            raise AssertionError(f"flow view map mismatch: {flow}")
        if flow.get("toolTabMap") != tab_tool_map:
            raise AssertionError(f"flow tool tab map mismatch: {flow}")
        if flow.get("actionSurfaceProofs") != action_surface_proofs:
            raise AssertionError(f"flow action surface proof map mismatch: {flow}")
        if flow.get("agentLoopPhaseCount") != agent_loop.get("loopPhaseCount"):
            raise AssertionError(f"flow agent loop phase count mismatch: {flow}")
        if flow.get("functionFlowCount") != functions.get("functionCount"):
            raise AssertionError(f"flow function count mismatch: {flow}")

        qa_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/tab-tool-function-flow" not in qa_routes:
            raise AssertionError(f"state routes missing tab-tool-function flow: {qa_routes}")

        tabs_group = (index.get("groups") or {}).get("tabsAndSessions") or {}
        if tabs_group.get("tabToolFunctionFlowCount") != flow.get("tabCount"):
            raise AssertionError(f"coverage index tab-tool-function count mismatch: {index}")
        if tabs_group.get("tabToolFunctionFlowParity") != flow.get("tabParity"):
            raise AssertionError(f"coverage index tab-tool-function parity mismatch: {index}")
        if tabs_group.get("tabToolFunctionFlowProofFileParity") != flow.get("proofFileParity"):
            raise AssertionError(f"coverage index tab-tool-function proof parity mismatch: {index}")

        docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
        for token in ["/qa/tab-tool-function-flow", "tab-tool-function-flow-proof.py", "tabToolFunctionFlowCount"]:
            if token not in docs_text:
                raise AssertionError(f"docs missing tab-tool-function token {token}")

        print("tab-tool-function-flow proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"tab-tool-function-flow proof failed: {exc}", flush=True)
        raise SystemExit(1)
