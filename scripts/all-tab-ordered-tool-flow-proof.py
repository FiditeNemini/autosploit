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
from typing import Any

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-05-all-tab-ordered-tool-flow.json"
CHAINED_ARTIFACT = ROOT / "docs/live-proofs/2026-07-04-chained-tool-workflow.json"
EXPECTED_TABS = ["recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"]
EXPECTED_WORKFLOWS = [
    {
        "id": "user_named_full_surface_order",
        "tabs": ["recon", "web", "network", "creds", "exploit", "post", "supplyChain", "osint", "report", "stash"],
    },
    {
        "id": "external_discovery_to_report_and_stash",
        "tabs": ["recon", "web", "supplyChain", "exploit", "post", "report", "stash"],
    },
    {
        "id": "credentialed_network_path",
        "tabs": ["network", "creds", "exploit", "post", "report", "stash"],
    },
    {
        "id": "osint_to_credential_path",
        "tabs": ["osint", "recon", "network", "creds", "report", "stash"],
    },
    {
        "id": "reverse_full_surface_order",
        "tabs": ["stash", "report", "osint", "supplyChain", "post", "exploit", "creds", "network", "web", "recon"],
    },
    {
        "id": "cve_first_supply_chain_retriage",
        "tabs": ["supplyChain", "web", "recon", "network", "report", "stash"],
    },
    {
        "id": "report_stash_reopen_loop",
        "tabs": ["report", "stash", "recon", "osint", "supplyChain", "report", "stash"],
    },
    {
        "id": "post_to_recon_retriage",
        "tabs": ["post", "exploit", "recon", "web", "network", "report", "stash"],
    },
    {
        "id": "osint_first_public_to_supply_chain",
        "tabs": ["osint", "supplyChain", "web", "recon", "report", "stash"],
    },
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


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def process_evidence() -> dict[str, Any]:
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


def proof_file_parity(proofs: list[str]) -> bool:
    return all((ROOT / "scripts" / proof).is_file() for proof in proofs)


def authorization_policy_count(tool_row: dict[str, Any]) -> int:
    policies = tool_row.get("authorizationPolicies")
    if isinstance(policies, dict):
        return len(policies)
    return int(tool_row.get("authorizationPolicyCount") or 0)


def build_route_indexes(
    tab_flow: dict[str, Any],
    action_matrix: dict[str, Any],
    tool_matrix: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    tabs = {row.get("tab"): row for row in tab_flow.get("flows") or [] if row.get("tab")}
    surfaces: dict[str, dict[str, Any]] = {}
    for row in action_matrix.get("surfaceRows") or []:
        for tab in row.get("tabs") or []:
            surfaces[tab] = row
    tools = {row.get("name"): row for row in tool_matrix.get("tools") or [] if row.get("name")}
    return tabs, surfaces, tools


def build_workflow_row(
    spec: dict[str, Any],
    tabs_by_name: dict[str, dict[str, Any]],
    surfaces_by_tab: dict[str, dict[str, Any]],
    tools_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    tab_rows: list[dict[str, Any]] = []
    route_sequence: list[str] = []
    tool_sequence: list[str] = []
    action_surface_sequence: list[str] = []
    proof_sequence: list[str] = []
    state_key_sequence: list[str] = []

    for tab in spec["tabs"]:
        tab_row = tabs_by_name.get(tab) or {}
        surface = surfaces_by_tab.get(tab) or {}
        tools = tab_row.get("tools") or []
        surface_routes = surface.get("routes") or []
        surface_proofs = surface.get("proofs") or []
        state_keys = surface.get("actionStateKeys") or []
        execution_rows = [tools_by_name.get(tool) or {} for tool in tools]
        missing_execution_rows = [tool for tool, row in zip(tools, execution_rows) if not row]
        missing_authorization_rows = [
            tool
            for tool, row in zip(tools, execution_rows)
            if row and authorization_policy_count(row) == 0
        ]
        missing_source_hook_rows = [
            tool
            for tool, row in zip(tools, execution_rows)
            if row and not row.get("sourceHooks")
        ]

        if not tab_row:
            failures.append(f"{tab}:missing_tab_flow_row")
        if not surface:
            failures.append(f"{tab}:missing_action_surface")
        if not tools:
            failures.append(f"{tab}:missing_tool_schema")
        if not surface_routes:
            failures.append(f"{tab}:missing_action_routes")
        if not surface_proofs or not proof_file_parity(surface_proofs):
            failures.append(f"{tab}:missing_surface_proofs")
        if not state_keys:
            failures.append(f"{tab}:missing_action_state_keys")
        if missing_execution_rows:
            failures.append(f"{tab}:missing_execution_rows:{','.join(missing_execution_rows)}")
        if missing_authorization_rows:
            failures.append(f"{tab}:missing_authorization_policies:{','.join(missing_authorization_rows)}")
        if missing_source_hook_rows:
            failures.append(f"{tab}:missing_source_hooks:{','.join(missing_source_hook_rows)}")

        if surface_routes:
            route_sequence.append(surface_routes[0])
        if tools:
            tool_sequence.append(tools[0])
        if surface.get("surface"):
            action_surface_sequence.append(surface["surface"])
        proof_sequence.extend(surface_proofs)
        state_key_sequence.extend(state_keys)
        tab_rows.append(
            {
                "tab": tab,
                "view": tab_row.get("view"),
                "tools": tools,
                "toolCount": len(tools),
                "actionSurface": surface.get("surface"),
                "routeCount": len(surface_routes),
                "routes": surface_routes,
                "proofs": surface_proofs,
                "stateKeys": state_keys,
                "executionSources": sorted(set(row.get("execution") for row in execution_rows if row.get("execution"))),
                "authorizationPolicyCount": max((authorization_policy_count(row) for row in execution_rows), default=0),
                "hasSubtabs": tab_row.get("hasSubtabs"),
                "subtabCount": tab_row.get("subtabCount"),
            }
        )

    return {
        "id": spec["id"],
        "status": "PASS" if not failures else "FAIL",
        "tabs": spec["tabs"],
        "tabRows": tab_rows,
        "toolSequence": tool_sequence,
        "routeSequence": route_sequence,
        "actionSurfaceSequence": action_surface_sequence,
        "proofSequence": sorted(set(proof_sequence)),
        "stateKeySequence": sorted(set(state_key_sequence)),
        "failures": failures,
    }


def model_chain_evidence() -> dict[str, Any]:
    chained = json.loads(CHAINED_ARTIFACT.read_text(encoding="utf-8"))
    rows = chained.get("rows") or []
    qwen_rows = [row for row in rows if str(row.get("id") or "").startswith("qwen") and row.get("status") == "PASS"]
    models = sorted(set(row.get("model") for row in qwen_rows if row.get("model")))
    ordered_tool_chains = {
        row.get("id"): row.get("requiredTools")
        for row in rows
        if row.get("status") == "PASS"
    }
    return {
        "artifact": str(CHAINED_ARTIFACT.relative_to(ROOT)),
        "ok": chained.get("ok") is True,
        "proofType": chained.get("proofType"),
        "rowCount": len(rows),
        "qwenPassRowCount": len(qwen_rows),
        "models": models,
        "hasQwen27": any("27B" in model for model in models),
        "hasQwen35": any("35B" in model for model in models),
        "orderedToolChains": ordered_tool_chains,
    }


def all_tool_coverage(
    workflow_rows: list[dict[str, Any]],
    tools_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    covered_tools: set[str] = set()
    covered_tabs: dict[str, list[str]] = {}
    for workflow in workflow_rows:
        for tab_row in workflow.get("tabRows") or []:
            tab = tab_row.get("tab") or ""
            for tool in tab_row.get("tools") or []:
                covered_tools.add(tool)
                covered_tabs.setdefault(tool, [])
                if tab and tab not in covered_tabs[tool]:
                    covered_tabs[tool].append(tab)

    all_tools = set(tools_by_name)
    missing_workflow_tools = sorted(all_tools.difference(covered_tools))
    missing_execution_owners = sorted(
        name for name, row in tools_by_name.items()
        if row.get("execution") not in {"callback", "subprocess"}
    )
    missing_source_hooks = sorted(
        name for name, row in tools_by_name.items()
        if not row.get("sourceHooks")
    )
    missing_authorization_policies = sorted(
        name for name, row in tools_by_name.items()
        if authorization_policy_count(row) == 0
    )
    execution_counts: dict[str, int] = {}
    for row in tools_by_name.values():
        execution = row.get("execution") or "missing"
        execution_counts[execution] = execution_counts.get(execution, 0) + 1

    all_executable_authorized = not (
        missing_workflow_tools
        or missing_execution_owners
        or missing_source_hooks
        or missing_authorization_policies
    )
    return {
        "toolCount": len(all_tools),
        "coveredToolCount": len(covered_tools.intersection(all_tools)),
        "coveredTools": sorted(covered_tools.intersection(all_tools)),
        "allToolsInOrderedWorkflows": not missing_workflow_tools,
        "allToolsHaveExecutionOwners": not missing_execution_owners,
        "allToolsHaveSourceHooks": not missing_source_hooks,
        "allToolsHaveAuthorizationPolicies": not missing_authorization_policies,
        "allToolsExecutableAndAuthorized": all_executable_authorized,
        "missingWorkflowTools": missing_workflow_tools,
        "missingExecutionOwners": missing_execution_owners,
        "missingSourceHooks": missing_source_hooks,
        "missingAuthorizationPolicies": missing_authorization_policies,
        "executionCounts": execution_counts,
        "authorizationPolicyCount": max((authorization_policy_count(row) for row in tools_by_name.values()), default=0),
        "toolTabs": {name: sorted(tabs) for name, tabs in sorted(covered_tabs.items()) if name in all_tools},
    }


def assert_report(report: dict[str, Any]) -> None:
    if report.get("ok") is not True:
        raise AssertionError(f"all-tab ordered tool flow failed: {report}")
    if report.get("tabs") != EXPECTED_TABS:
        raise AssertionError(f"tab order mismatch: {report}")
    if report.get("workflowCount") != len(EXPECTED_WORKFLOWS):
        raise AssertionError(f"workflow count mismatch: {report}")
    if report.get("tabFlowRouteParity") is not True:
        raise AssertionError(f"tab-flow route parity failed: {report}")
    if report.get("actionSurfaceRouteParity") is not True:
        raise AssertionError(f"action-surface route parity failed: {report}")
    if report.get("toolExecutionRouteParity") is not True:
        raise AssertionError(f"tool-execution route parity failed: {report}")
    diversity = report.get("orderDiversity") or {}
    if diversity.get("hasFullForwardOrder") is not True or diversity.get("hasFullReverseOrder") is not True:
        raise AssertionError(f"workflow order diversity missing full forward/reverse coverage: {diversity}")
    if diversity.get("hasRepeatedTabWorkflow") is not True:
        raise AssertionError(f"workflow order diversity missing repeated-tab coverage: {diversity}")
    model = report.get("modelChainEvidence") or {}
    if model.get("ok") is not True or model.get("hasQwen27") is not True or model.get("hasQwen35") is not True:
        raise AssertionError(f"model chain evidence incomplete: {model}")
    all_tools = report.get("allToolCoverage") or {}
    if all_tools.get("allToolsExecutableAndAuthorized") is not True:
        raise AssertionError(f"all-tool execution/authorization coverage incomplete: {all_tools}")
    if all_tools.get("toolCount") != all_tools.get("coveredToolCount"):
        raise AssertionError(f"all-tool ordered workflow coverage incomplete: {all_tools}")


def order_diversity(workflow_rows: list[dict[str, Any]]) -> dict[str, Any]:
    first_tabs = sorted(set((row.get("tabs") or [""])[0] for row in workflow_rows if row.get("tabs")))
    last_tabs = sorted(set((row.get("tabs") or [""])[-1] for row in workflow_rows if row.get("tabs")))
    repeated_tab_workflows = []
    for row in workflow_rows:
        tabs = row.get("tabs") or []
        if len(tabs) != len(set(tabs)):
            repeated_tab_workflows.append(row.get("id"))
    return {
        "hasFullForwardOrder": any(row.get("tabs") == EXPECTED_TABS for row in workflow_rows),
        "hasFullReverseOrder": any(row.get("tabs") == list(reversed(EXPECTED_TABS)) for row in workflow_rows),
        "hasRepeatedTabWorkflow": bool(repeated_tab_workflows),
        "repeatedTabWorkflowIds": repeated_tab_workflows,
        "firstTabs": first_tabs,
        "firstTabCount": len(first_tabs),
        "lastTabs": last_tabs,
        "lastTabCount": len(last_tabs),
        "workflowIds": [row.get("id") for row in workflow_rows],
    }


def build_report(state: dict[str, Any], tab_flow: dict[str, Any], action_matrix: dict[str, Any], tool_matrix: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    tabs_by_name, surfaces_by_tab, tools_by_name = build_route_indexes(tab_flow, action_matrix, tool_matrix)
    workflow_rows = [
        build_workflow_row(spec, tabs_by_name, surfaces_by_tab, tools_by_name)
        for spec in EXPECTED_WORKFLOWS
    ]
    tabs_sessions = (index.get("groups") or {}).get("tabsAndSessions") or {}
    tools_group = (index.get("groups") or {}).get("toolsAndParsers") or {}
    state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
    model_evidence = model_chain_evidence()
    tool_coverage = all_tool_coverage(workflow_rows, tools_by_name)
    all_pass = all(row["status"] == "PASS" for row in workflow_rows)
    diversity = order_diversity(workflow_rows)
    route_parity = {
        "tabFlow": tab_flow.get("ok") is True and "/qa/tab-tool-function-flow" in state_routes,
        "actionSurface": action_matrix.get("ok") is True and "/qa/tab-action-surface-matrix" in state_routes,
        "toolExecution": tool_matrix.get("ok") is True and "/qa/tool-execution-matrix" in state_routes,
    }
    return {
        "ok": all_pass
        and all(route_parity.values())
        and tool_coverage["allToolsExecutableAndAuthorized"]
        and tool_coverage["toolCount"] == tool_coverage["coveredToolCount"]
        and model_evidence["ok"]
        and model_evidence["hasQwen27"]
        and model_evidence["hasQwen35"],
        "proofType": "all-tab-ordered-tool-flow-live-route",
        "generatedAt": timestamp(),
        "proofLevel": "live-route-all-tab-wiring-plus-existing-real-qwen-ordered-tool-chain",
        "tabs": EXPECTED_TABS,
        "tabCount": len(EXPECTED_TABS),
        "workflowCount": len(workflow_rows),
        "workflowRows": workflow_rows,
        "orderDiversity": diversity,
        "statusCounts": {
            "PASS": sum(1 for row in workflow_rows if row["status"] == "PASS"),
            "FAIL": sum(1 for row in workflow_rows if row["status"] == "FAIL"),
        },
        "tabFlowRouteParity": route_parity["tabFlow"],
        "actionSurfaceRouteParity": route_parity["actionSurface"],
        "toolExecutionRouteParity": route_parity["toolExecution"],
        "routeEvidence": {
            "tabToolFunctionFlow": {
                "route": "/qa/tab-tool-function-flow",
                "tabCount": tab_flow.get("tabCount"),
                "proofFileParity": tab_flow.get("proofFileParity"),
                "coverageIndexMirror": tabs_sessions.get("tabToolFunctionFlowCount"),
            },
            "tabActionSurfaceMatrix": {
                "route": "/qa/tab-action-surface-matrix",
                "surfaceCount": action_matrix.get("surfaceCount"),
                "proofFileParity": action_matrix.get("proofFileParity"),
                "coverageIndexMirror": tabs_sessions.get("tabActionSurfaceMatrixCount"),
            },
            "toolExecutionMatrix": {
                "route": "/qa/tool-execution-matrix",
                "toolCount": tool_matrix.get("toolCount"),
                "proofFileParity": tool_matrix.get("proofFileParity"),
                "coverageIndexMirror": tools_group.get("toolExecutionMatrixCount"),
            },
        },
        "allToolCoverage": tool_coverage,
        "modelChainEvidence": model_evidence,
        "stateEvidence": {
            "engineRunning": bool(state.get("engineRunning")),
            "enginePort": state.get("enginePort"),
            "healthStatus": state.get("healthStatus"),
            "activeTab": state.get("activeTab"),
        },
        "processEvidence": process_evidence(),
    }


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    env["EXPLOITBOT_SKIP_APP_PROOF_LOCK"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        state = request("GET", "/state")
        tab_flow = request("GET", "/qa/tab-tool-function-flow")
        action_matrix = request("GET", "/qa/tab-action-surface-matrix")
        tool_matrix = request("GET", "/qa/tool-execution-matrix")
        index = request("GET", "/qa/coverage-index", timeout=120.0)

        report = build_report(state, tab_flow, action_matrix, tool_matrix, index)
        assert_report(report)
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"all-tab ordered tool flow proof passed and wrote {ARTIFACT}")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        with app_proof_lock("all-tab-ordered-tool-flow-proof.py"):
            run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"all-tab ordered tool flow proof failed: {exc}", flush=True)
        raise SystemExit(1)
