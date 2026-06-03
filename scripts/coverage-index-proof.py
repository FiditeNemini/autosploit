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

REQUIRED_ENDPOINTS = {
    "/state",
    "/messages",
    "/results",
    "/qa/tool-coverage",
    "/qa/subtab-coverage",
    "/qa/subtab-lifecycle-matrix",
    "/qa/endpoint-inventory",
    "/qa/endpoint-route-matrix",
    "/qa/action-state-inventory",
    "/qa/view-inventory",
    "/qa/function-flow-inventory",
    "/qa/function-proof-matrix",
    "/qa/service-inventory",
    "/qa/service-function-matrix",
    "/qa/model-state-inventory",
    "/qa/model-state-function-matrix",
    "/qa/proof-suite-inventory",
    "/qa/agent-loop-coverage",
    "/qa/agent-loop-phase-matrix",
    "/qa/agent-tool-authorization-coverage",
    "/qa/tab-tool-function-flow",
    "/qa/tool-execution-matrix",
    "/qa/tool-flow-coverage",
    "/qa/deep-runtime-flow-coverage",
    "/qa/runtime-coverage",
    "/qa/python-runtime-inventory",
    "/qa/engine-python-runtime",
    "/qa/agent-flow-inventory",
    "/qa/context-coverage",
    "/qa/context-flow-matrix",
    "/qa/evidence-lifecycle-coverage",
    "/qa/evidence-lifecycle-flow-matrix",
    "/qa/cve-taxonomy-matrix",
    "/qa/settings-coverage",
    "/qa/settings-surface-matrix",
    "/qa/visual-coverage",
    "/qa/visual-surface-matrix",
    "/qa/theme-inventory",
    "/qa/theme-token-matrix",
    "/qa/session-coverage",
    "/qa/session-workflow-matrix",
    "/qa/tab-action-coverage",
    "/qa/tab-action-surface-matrix",
    "/qa/tab-proof-family-matrix",
    "/qa/chat-coverage",
    "/qa/recon-coverage",
    "/qa/web-coverage",
    "/qa/network-coverage",
    "/qa/creds-coverage",
    "/qa/exploit-coverage",
    "/qa/post-coverage",
    "/qa/osint-coverage",
    "/qa/report-coverage",
    "/qa/stash-coverage",
    "/qa/result-parser-coverage",
    "/qa/parser-tool-matrix",
    "/qa/tool-family-fanout-coverage",
    "/qa/proof-ledger",
    "/qa/proof-category-matrix",
    "/qa/artifact-ledger",
    "/qa/artifact-manifest-matrix",
    "/qa/checkpoint-ledger",
    "/qa/audit-ledger",
    "/qa/gap-ledger",
    "/qa/release-readiness",
    "/qa/beta-readiness-coverage",
}

REQUIRED_PROOFS = {
    "app-qa-matrix-smoke-proof.py",
    "endpoint-inventory-proof.py",
    "endpoint-route-matrix-proof.py",
    "action-state-inventory-proof.py",
    "view-inventory-proof.py",
    "function-flow-inventory-proof.py",
    "function-proof-matrix-proof.py",
    "service-inventory-proof.py",
    "service-function-matrix-proof.py",
    "model-state-inventory-proof.py",
    "model-state-function-matrix-proof.py",
    "proof-suite-inventory-proof.py",
    "proof-category-matrix-proof.py",
    "tool-registry-coverage-proof.py",
    "subtab-coverage-proof.py",
    "subtab-lifecycle-matrix-proof.py",
    "agent-loop-coverage-proof.py",
    "agent-loop-phase-matrix-proof.py",
    "agent-tool-authorization-proof.py",
    "agent-live-tool-status-proof.py",
    "tab-tool-function-flow-proof.py",
    "tool-execution-matrix-proof.py",
    "tool-flow-coverage-proof.py",
    "deep-runtime-flow-coverage-proof.py",
    "tool-catalog-detail-proof.py",
    "runtime-coverage-proof.py",
    "python-runtime-inventory-proof.py",
    "engine-python-runtime-resolution-proof.py",
    "agent-flow-inventory-proof.py",
    "context-coverage-proof.py",
    "context-flow-matrix-proof.py",
    "evidence-lifecycle-coverage-proof.py",
    "evidence-lifecycle-flow-matrix-proof.py",
    "cve-taxonomy-matrix-proof.py",
    "settings-coverage-proof.py",
    "settings-surface-matrix-proof.py",
    "visual-coverage-proof.py",
    "visual-surface-matrix-proof.py",
    "theme-inventory-proof.py",
    "theme-token-matrix-proof.py",
    "session-coverage-proof.py",
    "session-workflow-matrix-proof.py",
    "terminal-tool-paths-proof.py",
    "tab-action-coverage-proof.py",
    "tab-action-surface-matrix-proof.py",
    "tab-proof-family-matrix-proof.py",
    "chat-coverage-proof.py",
    "recon-coverage-proof.py",
    "web-coverage-proof.py",
    "network-coverage-proof.py",
    "creds-coverage-proof.py",
    "exploit-coverage-proof.py",
    "post-coverage-proof.py",
    "osint-coverage-proof.py",
    "report-coverage-proof.py",
    "stash-coverage-proof.py",
    "result-parser-routing-proof.py",
    "parser-tool-matrix-proof.py",
    "tool-family-fanout-coverage-proof.py",
    "proof-ledger-proof.py",
    "artifact-ledger-proof.py",
    "artifact-manifest-matrix-proof.py",
    "checkpoint-ledger-proof.py",
    "audit-ledger-proof.py",
    "gap-ledger-proof.py",
    "docs-inventory-parity-proof.py",
    "release-readiness-proof.py",
    "release-app-live-qwen-proof.py",
    "release-app-qwen-cross-restart-cache-proof.py",
    "release-app-live-minimax-proof.py",
    "beta-readiness-coverage-proof.py",
}

REQUIRED_GROUPS = {
    "appState",
    "chatAndContext",
    "runtimeAndCache",
    "settingsAndVisuals",
    "toolsAndParsers",
    "tabsAndSessions",
    "releaseReadiness",
}

EXPECTED_FAMILY_FANOUT_TOOLS = {
    "recon": "nmap",
    "web": "nuclei",
    "network": "netexec",
    "creds": "hashcat",
    "exploit": "metasploit",
    "post": "linpeas",
    "osint": "gowitness",
}

EXPECTED_RESULT_PARSER_STRUCTURED_TOOLS = [
    "arjun",
    "dalfox",
    "dnsx",
    "exiftool",
    "feroxbuster",
    "ffuf",
    "gowitness",
    "graphqlmap",
    "haiti",
    "hashcat",
    "holehe",
    "httpx",
    "hydra",
    "impacket",
    "jwt_tool",
    "katana",
    "linpeas",
    "masscan",
    "metasploit",
    "netexec",
    "nmap",
    "nuclei",
    "sherlock",
    "snmpwalk",
    "sqlmap",
    "subfinder",
    "testssl",
    "theharvester",
    "trufflehog",
    "wpscan",
]

EXPECTED_RESULT_PARSER_RAW_ONLY_TOOLS = [
    "bettercap",
    "chisel",
    "pwncat",
    "sliver",
    "tshark",
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


def assert_coverage_index() -> None:
    seeded = request("POST", "/qa/seed-result-parser-fixture")
    if seeded.get("ok") is not True:
        raise AssertionError(f"result parser fixture seed failed: {seeded}")
    state = request("GET", "/state")
    index = request("GET", "/qa/coverage-index")
    proof = request("GET", "/qa/proof-ledger")
    artifact = request("GET", "/qa/artifact-ledger")
    artifact_manifest_matrix = request("GET", "/qa/artifact-manifest-matrix")
    checkpoint = request("GET", "/qa/checkpoint-ledger")
    audit = request("GET", "/qa/audit-ledger")
    gap = request("GET", "/qa/gap-ledger")

    if index.get("ok") is not True:
        raise AssertionError(f"/qa/coverage-index failed: {index}")
    if index.get("endpointCount", 0) < len(REQUIRED_ENDPOINTS):
        raise AssertionError(f"coverage index endpoint count mismatch: {index}")
    if index.get("proofCount", 0) < len(REQUIRED_PROOFS):
        raise AssertionError(f"coverage index proof count mismatch: {index}")

    endpoints = set(index.get("endpoints") or [])
    missing_endpoints = sorted(REQUIRED_ENDPOINTS.difference(endpoints))
    if missing_endpoints:
        raise AssertionError(f"coverage index missing endpoints {missing_endpoints}: {index}")

    proofs = set(index.get("proofs") or [])
    missing_proofs = sorted(REQUIRED_PROOFS.difference(proofs))
    if missing_proofs:
        raise AssertionError(f"coverage index missing proofs {missing_proofs}: {index}")
    missing_files = sorted(name for name in REQUIRED_PROOFS if not (ROOT / "scripts" / name).is_file())
    if missing_files:
        raise AssertionError(f"coverage index names non-existent proof files: {missing_files}")

    groups = index.get("groups") or {}
    missing_groups = sorted(name for name in REQUIRED_GROUPS if name not in groups)
    if missing_groups:
        raise AssertionError(f"coverage index missing groups {missing_groups}: {index}")
    for name, group in groups.items():
        endpoints_for_group = group.get("endpoints") or []
        proofs_for_group = group.get("proofs") or []
        if group.get("ok") is not True:
            raise AssertionError(f"coverage index group missing ok health {name}: {group}")
        if group.get("proofFileParity") is not True:
            raise AssertionError(f"coverage index group proof-file parity mismatch {name}: {group}")
        if not endpoints_for_group:
            raise AssertionError(f"coverage index group has no endpoints {name}: {group}")
        if not proofs_for_group:
            raise AssertionError(f"coverage index group has no proofs {name}: {group}")
        if group.get("endpointCount") != len(endpoints_for_group):
            raise AssertionError(f"coverage index group endpoint count mismatch {name}: {group}")
        if group.get("proofCount") != len(proofs_for_group):
            raise AssertionError(f"coverage index group proof count mismatch {name}: {group}")
    app_state_group = groups.get("appState") or {}
    if "docs-inventory-parity-proof.py" not in (app_state_group.get("proofs") or []):
        raise AssertionError(f"coverage index app state missing docs inventory parity proof: {app_state_group}")
    qa = state.get("qaCoverage") or {}
    if app_state_group.get("stateRoutes") != qa.get("stateRoutes"):
        raise AssertionError(f"coverage index app state route list mismatch: {app_state_group}")
    if app_state_group.get("stateRouteCount", 0) < 14:
        raise AssertionError(f"coverage index app state route count mismatch: {app_state_group}")
    endpoint_inventory = request("GET", "/qa/endpoint-inventory")
    if endpoint_inventory.get("ok") is not True:
        raise AssertionError(f"endpoint inventory route failed: {endpoint_inventory}")
    if endpoint_inventory.get("routeParity") is not True:
        raise AssertionError(f"endpoint inventory route parity mismatch: {endpoint_inventory}")
    if endpoint_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"endpoint inventory proof-file parity mismatch: {endpoint_inventory}")
    if app_state_group.get("endpointInventoryRouteCount") != endpoint_inventory.get("routeCount"):
        raise AssertionError(f"coverage index endpoint inventory route count mismatch: {app_state_group}")
    if app_state_group.get("endpointInventoryGroupCounts") != endpoint_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index endpoint inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("endpointInventoryProofFileParity") != endpoint_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index endpoint inventory proof parity mismatch: {app_state_group}")
    endpoint_route_matrix = request("GET", "/qa/endpoint-route-matrix")
    if endpoint_route_matrix.get("ok") is not True:
        raise AssertionError(f"endpoint route matrix route failed: {endpoint_route_matrix}")
    if endpoint_route_matrix.get("routeCount") != endpoint_inventory.get("routeCount"):
        raise AssertionError(f"endpoint route matrix count mismatch: {endpoint_route_matrix}")
    if endpoint_route_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"endpoint route matrix owner parity mismatch: {endpoint_route_matrix}")
    if endpoint_route_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"endpoint route matrix proof parity mismatch: {endpoint_route_matrix}")
    if app_state_group.get("endpointRouteMatrixCount") != endpoint_route_matrix.get("routeCount"):
        raise AssertionError(f"coverage index endpoint route matrix count mismatch: {app_state_group}")
    if app_state_group.get("endpointRouteMatrixProofOwnerFileParity") != endpoint_route_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index endpoint route matrix owner parity mismatch: {app_state_group}")
    if app_state_group.get("endpointRouteMatrixProofFileParity") != endpoint_route_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index endpoint route matrix proof parity mismatch: {app_state_group}")
    if app_state_group.get("endpointRouteMatrixStateRouteCount") != endpoint_route_matrix.get("stateRouteCount"):
        raise AssertionError(f"coverage index endpoint route matrix state route count mismatch: {app_state_group}")
    action_state_inventory = request("GET", "/qa/action-state-inventory")
    if action_state_inventory.get("ok") is not True:
        raise AssertionError(f"action-state inventory route failed: {action_state_inventory}")
    if action_state_inventory.get("snapshotParity") is not True:
        raise AssertionError(f"action-state inventory snapshot parity mismatch: {action_state_inventory}")
    if action_state_inventory.get("stateFieldParity") is not True:
        raise AssertionError(f"action-state inventory state-field parity mismatch: {action_state_inventory}")
    if action_state_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"action-state inventory proof-file parity mismatch: {action_state_inventory}")
    if app_state_group.get("actionStateInventoryCount") != action_state_inventory.get("actionStateCount"):
        raise AssertionError(f"coverage index action-state inventory count mismatch: {app_state_group}")
    if app_state_group.get("actionStateInventoryGroups") != action_state_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index action-state inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("actionStateInventoryProofFileParity") != action_state_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index action-state inventory proof parity mismatch: {app_state_group}")
    view_inventory = request("GET", "/qa/view-inventory")
    if view_inventory.get("ok") is not True:
        raise AssertionError(f"view inventory route failed: {view_inventory}")
    if view_inventory.get("mainTabParity") is not True:
        raise AssertionError(f"view inventory main tab parity mismatch: {view_inventory}")
    if view_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"view inventory proof-file parity mismatch: {view_inventory}")
    if app_state_group.get("viewInventoryStructCount") != view_inventory.get("viewStructCount"):
        raise AssertionError(f"coverage index view inventory struct count mismatch: {app_state_group}")
    if app_state_group.get("viewInventoryGroupCounts") != view_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index view inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("viewInventoryMainTabViews") != view_inventory.get("mainTabViews"):
        raise AssertionError(f"coverage index view inventory tab map mismatch: {app_state_group}")
    if app_state_group.get("viewInventoryProofFileParity") != view_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index view inventory proof parity mismatch: {app_state_group}")
    function_flow_inventory = request("GET", "/qa/function-flow-inventory")
    if function_flow_inventory.get("ok") is not True:
        raise AssertionError(f"function-flow inventory route failed: {function_flow_inventory}")
    if function_flow_inventory.get("functionCount", 0) < 500:
        raise AssertionError(f"function-flow inventory function count too low: {function_flow_inventory}")
    if function_flow_inventory.get("groupParity") is not True:
        raise AssertionError(f"function-flow inventory group parity mismatch: {function_flow_inventory}")
    if function_flow_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"function-flow inventory proof-file parity mismatch: {function_flow_inventory}")
    if app_state_group.get("functionFlowInventoryCount") != function_flow_inventory.get("functionCount"):
        raise AssertionError(f"coverage index function-flow inventory count mismatch: {app_state_group}")
    if app_state_group.get("functionFlowInventoryGroupCounts") != function_flow_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index function-flow inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("functionFlowInventoryProofFileParity") != function_flow_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index function-flow inventory proof parity mismatch: {app_state_group}")
    function_proof_matrix = request("GET", "/qa/function-proof-matrix")
    if function_proof_matrix.get("ok") is not True:
        raise AssertionError(f"function proof matrix route failed: {function_proof_matrix}")
    if function_proof_matrix.get("functionCount") != function_flow_inventory.get("functionCount"):
        raise AssertionError(f"function proof matrix function count mismatch: {function_proof_matrix}")
    if function_proof_matrix.get("rowParity") is not True:
        raise AssertionError(f"function proof matrix row parity mismatch: {function_proof_matrix}")
    if function_proof_matrix.get("groupRouteParity") is not True:
        raise AssertionError(f"function proof matrix group route parity mismatch: {function_proof_matrix}")
    if function_proof_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"function proof matrix proof owner parity mismatch: {function_proof_matrix}")
    if function_proof_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"function proof matrix proof-file parity mismatch: {function_proof_matrix}")
    if app_state_group.get("functionProofMatrixCount") != function_proof_matrix.get("functionCount"):
        raise AssertionError(f"coverage index function proof matrix count mismatch: {app_state_group}")
    if app_state_group.get("functionProofMatrixRowParity") != function_proof_matrix.get("rowParity"):
        raise AssertionError(f"coverage index function proof matrix row parity mismatch: {app_state_group}")
    if app_state_group.get("functionProofMatrixGroupRouteParity") != function_proof_matrix.get("groupRouteParity"):
        raise AssertionError(f"coverage index function proof matrix group route parity mismatch: {app_state_group}")
    if app_state_group.get("functionProofMatrixProofOwnerFileParity") != function_proof_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index function proof matrix proof owner parity mismatch: {app_state_group}")
    if app_state_group.get("functionProofMatrixProofFileParity") != function_proof_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index function proof matrix proof-file parity mismatch: {app_state_group}")
    service_inventory = request("GET", "/qa/service-inventory")
    if service_inventory.get("ok") is not True:
        raise AssertionError(f"service inventory route failed: {service_inventory}")
    if service_inventory.get("functionCount", 0) < 150:
        raise AssertionError(f"service inventory function count too low: {service_inventory}")
    if service_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"service inventory proof-file parity mismatch: {service_inventory}")
    if app_state_group.get("serviceInventoryFileCount") != service_inventory.get("serviceFileCount"):
        raise AssertionError(f"coverage index service inventory file count mismatch: {app_state_group}")
    if app_state_group.get("serviceInventoryFunctionCount") != service_inventory.get("functionCount"):
        raise AssertionError(f"coverage index service inventory function count mismatch: {app_state_group}")
    if app_state_group.get("serviceInventoryGroupCounts") != service_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index service inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("serviceInventoryProofFileParity") != service_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index service inventory proof parity mismatch: {app_state_group}")
    service_function_matrix = request("GET", "/qa/service-function-matrix")
    if service_function_matrix.get("ok") is not True:
        raise AssertionError(f"service function matrix route failed: {service_function_matrix}")
    if service_function_matrix.get("functionCount") != service_inventory.get("functionCount"):
        raise AssertionError(f"service function matrix count mismatch: {service_function_matrix}")
    if service_function_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"service function matrix owner parity mismatch: {service_function_matrix}")
    if service_function_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"service function matrix proof parity mismatch: {service_function_matrix}")
    if service_function_matrix.get("functionProofMatrixCount") != function_proof_matrix.get("functionCount"):
        raise AssertionError(f"service function matrix function proof count mismatch: {service_function_matrix}")
    if app_state_group.get("serviceFunctionMatrixCount") != service_function_matrix.get("functionCount"):
        raise AssertionError(f"coverage index service function matrix count mismatch: {app_state_group}")
    if app_state_group.get("serviceFunctionMatrixProofOwnerFileParity") != service_function_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index service function matrix owner parity mismatch: {app_state_group}")
    if app_state_group.get("serviceFunctionMatrixProofFileParity") != service_function_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index service function matrix proof parity mismatch: {app_state_group}")
    if app_state_group.get("serviceFunctionMatrixFunctionProofCount") != service_function_matrix.get("functionProofMatrixCount"):
        raise AssertionError(f"coverage index service function matrix function proof count mismatch: {app_state_group}")
    model_state_inventory = request("GET", "/qa/model-state-inventory")
    if model_state_inventory.get("ok") is not True:
        raise AssertionError(f"model-state inventory route failed: {model_state_inventory}")
    if model_state_inventory.get("fileCount", 0) < 6:
        raise AssertionError(f"model-state inventory file count too low: {model_state_inventory}")
    if model_state_inventory.get("functionCount", 0) < 150:
        raise AssertionError(f"model-state inventory function count too low: {model_state_inventory}")
    if model_state_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"model-state inventory proof-file parity mismatch: {model_state_inventory}")
    if app_state_group.get("modelStateInventoryFileCount") != model_state_inventory.get("fileCount"):
        raise AssertionError(f"coverage index model-state inventory file count mismatch: {app_state_group}")
    if app_state_group.get("modelStateInventoryTypeCount") != model_state_inventory.get("typeCount"):
        raise AssertionError(f"coverage index model-state inventory type count mismatch: {app_state_group}")
    if app_state_group.get("modelStateInventoryFunctionCount") != model_state_inventory.get("functionCount"):
        raise AssertionError(f"coverage index model-state inventory function count mismatch: {app_state_group}")
    if app_state_group.get("modelStateInventoryGroupCounts") != model_state_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index model-state inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("modelStateInventoryProofFileParity") != model_state_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index model-state inventory proof parity mismatch: {app_state_group}")
    model_state_function_matrix = request("GET", "/qa/model-state-function-matrix")
    if model_state_function_matrix.get("ok") is not True:
        raise AssertionError(f"model-state function matrix route failed: {model_state_function_matrix}")
    if model_state_function_matrix.get("functionCount") != model_state_inventory.get("functionCount"):
        raise AssertionError(f"model-state function matrix count mismatch: {model_state_function_matrix}")
    if model_state_function_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"model-state function matrix owner parity mismatch: {model_state_function_matrix}")
    if model_state_function_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"model-state function matrix proof parity mismatch: {model_state_function_matrix}")
    if model_state_function_matrix.get("functionProofMatrixCount") != function_proof_matrix.get("functionCount"):
        raise AssertionError(f"model-state function matrix function proof count mismatch: {model_state_function_matrix}")
    if app_state_group.get("modelStateFunctionMatrixCount") != model_state_function_matrix.get("functionCount"):
        raise AssertionError(f"coverage index model-state function matrix count mismatch: {app_state_group}")
    if app_state_group.get("modelStateFunctionMatrixProofOwnerFileParity") != model_state_function_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index model-state function matrix owner parity mismatch: {app_state_group}")
    if app_state_group.get("modelStateFunctionMatrixProofFileParity") != model_state_function_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index model-state function matrix proof parity mismatch: {app_state_group}")
    if app_state_group.get("modelStateFunctionMatrixFunctionProofCount") != model_state_function_matrix.get("functionProofMatrixCount"):
        raise AssertionError(f"coverage index model-state function matrix function proof count mismatch: {app_state_group}")
    proof_suite_inventory = request("GET", "/qa/proof-suite-inventory")
    if proof_suite_inventory.get("ok") is not True:
        raise AssertionError(f"proof-suite inventory route failed: {proof_suite_inventory}")
    if proof_suite_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"proof-suite inventory proof-file parity mismatch: {proof_suite_inventory}")
    if proof_suite_inventory.get("parseParity") is not True:
        raise AssertionError(f"proof-suite inventory parse parity mismatch: {proof_suite_inventory}")
    if proof_suite_inventory.get("fileCount", 0) < 120:
        raise AssertionError(f"proof-suite inventory file count too low: {proof_suite_inventory}")
    if proof_suite_inventory.get("routeTargetCount", 0) < 45:
        raise AssertionError(f"proof-suite inventory route target count too low: {proof_suite_inventory}")
    if proof_suite_inventory.get("launchesAppCount", 0) < 100:
        raise AssertionError(f"proof-suite inventory app-launching count too low: {proof_suite_inventory}")
    if proof_suite_inventory.get("visualProofCount", 0) < 20:
        raise AssertionError(f"proof-suite inventory visual proof count too low: {proof_suite_inventory}")
    if proof_suite_inventory.get("liveModelProofCount", 0) < 3:
        raise AssertionError(f"proof-suite inventory live model count too low: {proof_suite_inventory}")
    if app_state_group.get("proofSuiteInventoryFileCount") != proof_suite_inventory.get("fileCount"):
        raise AssertionError(f"coverage index proof-suite inventory file count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryGroupCounts") != proof_suite_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index proof-suite inventory group counts mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryRouteTargetCount") != proof_suite_inventory.get("routeTargetCount"):
        raise AssertionError(f"coverage index proof-suite inventory route target count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryLaunchesAppCount") != proof_suite_inventory.get("launchesAppCount"):
        raise AssertionError(f"coverage index proof-suite inventory launches-app count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryVisualProofCount") != proof_suite_inventory.get("visualProofCount"):
        raise AssertionError(f"coverage index proof-suite inventory visual count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryLiveModelProofCount") != proof_suite_inventory.get("liveModelProofCount"):
        raise AssertionError(f"coverage index proof-suite inventory live count mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryProofFileParity") != proof_suite_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index proof-suite inventory file parity mismatch: {app_state_group}")
    if app_state_group.get("proofSuiteInventoryParseParity") != proof_suite_inventory.get("parseParity"):
        raise AssertionError(f"coverage index proof-suite inventory parse parity mismatch: {app_state_group}")
    if app_state_group.get("contextHooks") != qa.get("contextHooks"):
        raise AssertionError(f"coverage index app state context hook list mismatch: {app_state_group}")
    if app_state_group.get("contextHookCount") != len(qa.get("contextHooks") or []):
        raise AssertionError(f"coverage index app state context hook count mismatch: {app_state_group}")
    if app_state_group.get("subtabStateTabs") != qa.get("subtabStateTabs"):
        raise AssertionError(f"coverage index app state subtab list mismatch: {app_state_group}")
    if app_state_group.get("subtabStateTabCount", 0) < 8:
        raise AssertionError(f"coverage index app state subtab count mismatch: {app_state_group}")
    if app_state_group.get("subtabStateProofs") != qa.get("subtabStateProofs"):
        raise AssertionError(f"coverage index app state subtab proof list mismatch: {app_state_group}")
    if app_state_group.get("subtabStateProofCount", 0) < 8:
        raise AssertionError(f"coverage index app state subtab proof count mismatch: {app_state_group}")
    subtab_coverage = request("GET", "/qa/subtab-coverage")
    subtab_lifecycle_matrix = request("GET", "/qa/subtab-lifecycle-matrix")
    if app_state_group.get("subtabStateProofFileParity") != subtab_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index app state subtab proof-file parity mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCount", 0) < 120:
        raise AssertionError(f"coverage index app state proof ledger count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerProofFileParity") != proof.get("proofFileParity"):
        raise AssertionError(f"coverage index app state proof-file parity mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryCounts") != proof.get("categoryCounts"):
        raise AssertionError(f"coverage index app state proof ledger category counts mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategorySurfaces") != proof.get("categorySurfaces"):
        raise AssertionError(f"coverage index app state proof ledger category surfaces mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategorySurfaceCount") != proof.get("categorySurfaceCount"):
        raise AssertionError(f"coverage index app state proof ledger category surface count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryOtherCount") != proof.get("categoryOtherCount"):
        raise AssertionError(f"coverage index app state proof ledger category other count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryTotalCount") != proof.get("categoryTotalCount"):
        raise AssertionError(f"coverage index app state proof ledger category total count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategoryParity") != proof.get("categoryParity"):
        raise AssertionError(f"coverage index app state proof ledger category parity mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerCategories") != proof.get("categories"):
        raise AssertionError(f"coverage index app state proof ledger category map mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerTabProofFamilies") != proof.get("tabProofFamilies"):
        raise AssertionError(f"coverage index app state proof ledger tab family map mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerTabProofFamilyCount") != proof.get("tabProofFamilyCount"):
        raise AssertionError(f"coverage index app state proof ledger tab family count mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerTabProofFamilyParity") != proof.get("tabProofFamilyParity"):
        raise AssertionError(f"coverage index app state proof ledger tab family parity mismatch: {app_state_group}")
    if app_state_group.get("proofLedgerTabProofFamilyFileParity") != proof.get("tabProofFamilyFileParity"):
        raise AssertionError(f"coverage index app state proof ledger tab family file parity mismatch: {app_state_group}")
    expected_categories = {
        name: category.get("count")
        for name, category in (proof.get("categories") or {}).items()
        if name in {"agent", "chat", "context", "release", "runtime", "settings", "tabs", "tools", "visual"}
    }
    if app_state_group.get("proofCategoryCounts") != expected_categories:
        raise AssertionError(f"coverage index app state proof category counts mismatch: {app_state_group}")
    if app_state_group.get("proofCategorySurfaces") != sorted(expected_categories):
        raise AssertionError(f"coverage index app state proof category surfaces mismatch: {app_state_group}")
    if app_state_group.get("proofCategorySurfaceCount") != len(expected_categories):
        raise AssertionError(f"coverage index app state proof category surface count mismatch: {app_state_group}")
    expected_category_total = sum(
        category.get("count", 0)
        for category in (proof.get("categories") or {}).values()
    )
    if app_state_group.get("proofCategoryTotalCount") != expected_category_total:
        raise AssertionError(f"coverage index app state proof category total mismatch: {app_state_group}")
    if app_state_group.get("proofCategoryTotalCount") != proof.get("proofCount"):
        raise AssertionError(f"coverage index app state proof category total does not match proof ledger: {app_state_group}")
    if app_state_group.get("proofCategoryParity") is not True:
        raise AssertionError(f"coverage index app state proof category parity flag mismatch: {app_state_group}")
    proof_category_matrix = request("GET", "/qa/proof-category-matrix")
    if proof_category_matrix.get("ok") is not True:
        raise AssertionError(f"proof category matrix route failed: {proof_category_matrix}")
    if app_state_group.get("proofCategoryMatrixCount") != proof_category_matrix.get("categoryCount"):
        raise AssertionError(f"coverage index app state proof category matrix count mismatch: {app_state_group}")
    if app_state_group.get("proofCategoryMatrixProofFileParity") != proof_category_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index app state proof category matrix proof parity mismatch: {app_state_group}")
    if app_state_group.get("proofCategoryMatrixCategoryProofFileParity") != proof_category_matrix.get("categoryProofFileParity"):
        raise AssertionError(f"coverage index app state proof category matrix category parity mismatch: {app_state_group}")
    if app_state_group.get("proofCategoryMatrixProofLedgerCount") != proof_category_matrix.get("proofLedgerCount"):
        raise AssertionError(f"coverage index app state proof category matrix ledger count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualManifestCount", 0) < 22:
        raise AssertionError(f"coverage index app state artifact visual count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualCaptureCount") != artifact.get("visualCaptureCount"):
        raise AssertionError(f"coverage index app state artifact visual capture count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualManifests") != artifact.get("visualManifests"):
        raise AssertionError(f"coverage index app state artifact visual manifests mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualManifestFileParity") != artifact.get("visualManifestFileParity"):
        raise AssertionError(f"coverage index app state artifact visual manifest file parity mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerVisualCaptureStatus") != artifact.get("visualCaptureStatus"):
        raise AssertionError(f"coverage index app state artifact visual capture status mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofCount", 0) < 18:
        raise AssertionError(f"coverage index app state artifact live count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofOkCount") != artifact.get("liveProofOkCount"):
        raise AssertionError(f"coverage index app state artifact live ok count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofs") != artifact.get("liveProofs"):
        raise AssertionError(f"coverage index app state artifact live proofs mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofFileParity") != artifact.get("liveProofFileParity"):
        raise AssertionError(f"coverage index app state artifact live proof file parity mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerLiveProofStatus") != artifact.get("liveProofStatus"):
        raise AssertionError(f"coverage index app state artifact live proof status mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerFailedLiveProofCount") != artifact.get("failedLiveProofCount"):
        raise AssertionError(f"coverage index app state artifact failed live proof count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerFailedLiveProofs") != artifact.get("failedLiveProofs"):
        raise AssertionError(f"coverage index app state artifact failed live proofs mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerKnownFailedLiveProofCount") != artifact.get("knownFailedLiveProofCount"):
        raise AssertionError(f"coverage index app state artifact known failed count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerKnownFailedLiveProofs") != artifact.get("knownFailedLiveProofs"):
        raise AssertionError(f"coverage index app state artifact known failed list mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerCurrentFailedLiveProofCount") != artifact.get("currentFailedLiveProofCount"):
        raise AssertionError(f"coverage index app state artifact current failed count mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerCurrentFailedLiveProofs") != artifact.get("currentFailedLiveProofs"):
        raise AssertionError(f"coverage index app state artifact current failed list mismatch: {app_state_group}")
    if app_state_group.get("artifactLedgerCurrentLiveProofFailureFree") != artifact.get("currentLiveProofFailureFree"):
        raise AssertionError(f"coverage index app state artifact current failure-free flag mismatch: {app_state_group}")
    if app_state_group.get("missingVisualCaptureCount", 1) != 0:
        raise AssertionError(f"coverage index app state missing visual captures: {app_state_group}")
    if app_state_group.get("missingVisualCaptures") != artifact.get("missingVisualCaptures"):
        raise AssertionError(f"coverage index app state missing visual capture list mismatch: {app_state_group}")
    if artifact_manifest_matrix.get("ok") is not True:
        raise AssertionError(f"artifact manifest matrix route failed: {artifact_manifest_matrix}")
    if app_state_group.get("artifactManifestMatrixCount") != artifact_manifest_matrix.get("manifestCount"):
        raise AssertionError(f"coverage index app state artifact manifest matrix count mismatch: {app_state_group}")
    if app_state_group.get("artifactManifestMatrixProofFileParity") != artifact_manifest_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index app state artifact manifest matrix proof parity mismatch: {app_state_group}")
    if app_state_group.get("artifactManifestMatrixManifestFileParity") != artifact_manifest_matrix.get("manifestFileParity"):
        raise AssertionError(f"coverage index app state artifact manifest matrix manifest parity mismatch: {app_state_group}")
    if app_state_group.get("artifactManifestMatrixCaptureFileParity") != artifact_manifest_matrix.get("captureFileParity"):
        raise AssertionError(f"coverage index app state artifact manifest matrix capture parity mismatch: {app_state_group}")
    if app_state_group.get("checkpointLedgerCount", 0) < 200:
        raise AssertionError(f"coverage index app state checkpoint ledger count mismatch: {app_state_group}")
    if app_state_group.get("checkpoints") != checkpoint.get("checkpoints"):
        raise AssertionError(f"coverage index app state checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("checkpointFileParity") != checkpoint.get("checkpointFileParity"):
        raise AssertionError(f"coverage index app state checkpoint file parity mismatch: {app_state_group}")
    if app_state_group.get("completeCheckpointCount") != checkpoint.get("completeCheckpointCount"):
        raise AssertionError(f"coverage index app state complete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("completeCheckpoints") != checkpoint.get("completeCheckpoints"):
        raise AssertionError(f"coverage index app state complete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("incompleteCheckpointCount") != len(checkpoint.get("incompleteCheckpoints") or []):
        raise AssertionError(f"coverage index app state incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("incompleteCheckpoints") != checkpoint.get("incompleteCheckpoints"):
        raise AssertionError(f"coverage index app state incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("legacyIncompleteCheckpointMaxNumber") != checkpoint.get("legacyIncompleteCheckpointMaxNumber"):
        raise AssertionError(f"coverage index app state legacy incomplete max checkpoint mismatch: {app_state_group}")
    if app_state_group.get("legacyIncompleteCheckpointCount") != checkpoint.get("legacyIncompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state legacy incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("legacyIncompleteCheckpoints") != checkpoint.get("legacyIncompleteCheckpoints"):
        raise AssertionError(f"coverage index app state legacy incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("currentIncompleteCheckpointCount") != checkpoint.get("currentIncompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state current incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("currentIncompleteCheckpoints") != checkpoint.get("currentIncompleteCheckpoints"):
        raise AssertionError(f"coverage index app state current incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("currentCheckpointDocsComplete") != checkpoint.get("currentCheckpointDocsComplete"):
        raise AssertionError(f"coverage index app state current checkpoint docs complete flag mismatch: {app_state_group}")
    if app_state_group.get("checkpointCompletionRatio") != checkpoint.get("checkpointCompletionRatio"):
        raise AssertionError(f"coverage index app state checkpoint ratio mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpoint") != checkpoint.get("latestCheckpoint"):
        raise AssertionError(f"coverage index app state latest checkpoint mismatch: {app_state_group}")
    if app_state_group.get("latestCheckpointNumber") != checkpoint.get("latestCheckpointNumber"):
        raise AssertionError(f"coverage index app state latest checkpoint number mismatch: {app_state_group}")
    if app_state_group.get("auditLedgerCount", 0) < 300:
        raise AssertionError(f"coverage index app state audit ledger count mismatch: {app_state_group}")
    if app_state_group.get("auditVisualManifestCount") != audit.get("visualManifestCount"):
        raise AssertionError(f"coverage index app state audit visual manifest count mismatch: {app_state_group}")
    if app_state_group.get("auditVisualManifestFileParity") != audit.get("visualManifestFileParity"):
        raise AssertionError(f"coverage index app state audit visual manifest file parity mismatch: {app_state_group}")
    if app_state_group.get("auditVisualCaptureCount") != audit.get("visualCaptureCount"):
        raise AssertionError(f"coverage index app state audit visual capture count mismatch: {app_state_group}")
    if app_state_group.get("auditMissingVisualCaptureCount") != audit.get("missingVisualCaptureCount"):
        raise AssertionError(f"coverage index app state audit missing visual capture count mismatch: {app_state_group}")
    if app_state_group.get("auditMissingVisualCaptures") != audit.get("missingVisualCaptures"):
        raise AssertionError(f"coverage index app state audit missing visual capture list mismatch: {app_state_group}")
    if app_state_group.get("auditLiveProofCount") != audit.get("liveProofCount"):
        raise AssertionError(f"coverage index app state audit live proof count mismatch: {app_state_group}")
    if app_state_group.get("auditLiveProofFileParity") != audit.get("liveProofFileParity"):
        raise AssertionError(f"coverage index app state audit live proof file parity mismatch: {app_state_group}")
    if app_state_group.get("auditLiveProofOkCount") != audit.get("liveProofOkCount"):
        raise AssertionError(f"coverage index app state audit live proof ok count mismatch: {app_state_group}")
    if app_state_group.get("auditFailedLiveProofCount") != audit.get("failedLiveProofCount"):
        raise AssertionError(f"coverage index app state audit failed live proof count mismatch: {app_state_group}")
    if app_state_group.get("auditFailedLiveProofs") != audit.get("failedLiveProofs"):
        raise AssertionError(f"coverage index app state audit failed live proof list mismatch: {app_state_group}")
    if app_state_group.get("auditKnownFailedLiveProofCount") != audit.get("knownFailedLiveProofCount"):
        raise AssertionError(f"coverage index app state audit known failed count mismatch: {app_state_group}")
    if app_state_group.get("auditKnownFailedLiveProofs") != audit.get("knownFailedLiveProofs"):
        raise AssertionError(f"coverage index app state audit known failed list mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentFailedLiveProofCount") != audit.get("currentFailedLiveProofCount"):
        raise AssertionError(f"coverage index app state audit current failed count mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentFailedLiveProofs") != audit.get("currentFailedLiveProofs"):
        raise AssertionError(f"coverage index app state audit current failed list mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentLiveProofFailureFree") != audit.get("currentLiveProofFailureFree"):
        raise AssertionError(f"coverage index app state audit current failure-free flag mismatch: {app_state_group}")
    if app_state_group.get("auditCheckpointCount") != audit.get("checkpointCount"):
        raise AssertionError(f"coverage index app state audit checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditCheckpointFileParity") != audit.get("checkpointFileParity"):
        raise AssertionError(f"coverage index app state audit checkpoint file parity mismatch: {app_state_group}")
    if app_state_group.get("auditCompleteCheckpointCount") != audit.get("completeCheckpointCount"):
        raise AssertionError(f"coverage index app state audit complete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditCheckpointCompletionRatio") != audit.get("checkpointCompletionRatio"):
        raise AssertionError(f"coverage index app state audit checkpoint completion ratio mismatch: {app_state_group}")
    if app_state_group.get("auditCompleteCheckpoints") != audit.get("completeCheckpoints"):
        raise AssertionError(f"coverage index app state audit complete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditIncompleteCheckpointCount") != audit.get("incompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state audit incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditIncompleteCheckpoints") != audit.get("incompleteCheckpoints"):
        raise AssertionError(f"coverage index app state audit incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditLegacyIncompleteCheckpointMaxNumber") != audit.get("legacyIncompleteCheckpointMaxNumber"):
        raise AssertionError(f"coverage index app state audit legacy incomplete max checkpoint mismatch: {app_state_group}")
    if app_state_group.get("auditLegacyIncompleteCheckpointCount") != audit.get("legacyIncompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state audit legacy incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditLegacyIncompleteCheckpoints") != audit.get("legacyIncompleteCheckpoints"):
        raise AssertionError(f"coverage index app state audit legacy incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentIncompleteCheckpointCount") != audit.get("currentIncompleteCheckpointCount"):
        raise AssertionError(f"coverage index app state audit current incomplete checkpoint count mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentIncompleteCheckpoints") != audit.get("currentIncompleteCheckpoints"):
        raise AssertionError(f"coverage index app state audit current incomplete checkpoint list mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentCheckpointDocsComplete") != audit.get("currentCheckpointDocsComplete"):
        raise AssertionError(f"coverage index app state audit current checkpoint docs complete flag mismatch: {app_state_group}")
    if app_state_group.get("auditLatestCheckpoint") != audit.get("latestCheckpoint"):
        raise AssertionError(f"coverage index app state audit latest checkpoint mismatch: {app_state_group}")
    if app_state_group.get("auditLatestCheckpointNumber") != audit.get("latestCheckpointNumber"):
        raise AssertionError(f"coverage index app state audit latest checkpoint number mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentGapCount") != audit.get("currentGapCount"):
        raise AssertionError(f"coverage index app state audit current gap count mismatch: {app_state_group}")
    if app_state_group.get("auditGapSource") != audit.get("gapSource"):
        raise AssertionError(f"coverage index app state audit gap source mismatch: {app_state_group}")
    if app_state_group.get("auditGapSourceDerived") != audit.get("gapSourceDerived"):
        raise AssertionError(f"coverage index app state audit gap source-derived flag mismatch: {app_state_group}")
    if app_state_group.get("auditGapSourcePathExists") != audit.get("gapSourcePathExists"):
        raise AssertionError(f"coverage index app state audit gap source path flag mismatch: {app_state_group}")
    if app_state_group.get("auditCurrentGaps") != audit.get("currentGaps"):
        raise AssertionError(f"coverage index app state audit current gap list mismatch: {app_state_group}")
    if app_state_group.get("auditNextGap") != audit.get("nextGap"):
        raise AssertionError(f"coverage index app state audit next gap mismatch: {app_state_group}")
    if app_state_group.get("auditGapSupportedFamilies") != audit.get("gapSupportedFamilies"):
        raise AssertionError(f"coverage index app state audit gap supported families mismatch: {app_state_group}")
    if app_state_group.get("auditUnsupportedMultimodalBlocked") != audit.get("unsupportedMultimodalBlocked"):
        raise AssertionError(f"coverage index app state audit unsupported multimodal block mismatch: {app_state_group}")
    if app_state_group.get("auditOpenGapIds") != audit.get("openGapIds"):
        raise AssertionError(f"coverage index app state audit open gap ids mismatch: {app_state_group}")
    if app_state_group.get("auditGapContracts") != audit.get("gapContracts"):
        raise AssertionError(f"coverage index app state audit gap contracts mismatch: {app_state_group}")
    if app_state_group.get("auditGapContractCount") != audit.get("gapContractCount"):
        raise AssertionError(f"coverage index app state audit gap contract count mismatch: {app_state_group}")
    if app_state_group.get("auditProofCount") != audit.get("proofCount"):
        raise AssertionError(f"coverage index app state audit proof count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerProofFileParity") != audit.get("proofLedgerProofFileParity"):
        raise AssertionError(f"coverage index app state audit proof-file parity mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategoryCounts") != audit.get("proofLedgerCategoryCounts"):
        raise AssertionError(f"coverage index app state audit source proof category counts mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategorySurfaces") != audit.get("proofLedgerCategorySurfaces"):
        raise AssertionError(f"coverage index app state audit source proof category surfaces mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategorySurfaceCount") != audit.get("proofLedgerCategorySurfaceCount"):
        raise AssertionError(f"coverage index app state audit source proof category surface count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategories") != audit.get("proofLedgerCategories"):
        raise AssertionError(f"coverage index app state audit source proof category map mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerTabProofFamilies") != audit.get("proofLedgerTabProofFamilies"):
        raise AssertionError(f"coverage index app state audit source proof tab family map mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerTabProofFamilyCount") != audit.get("proofLedgerTabProofFamilyCount"):
        raise AssertionError(f"coverage index app state audit source proof tab family count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerTabProofFamilyParity") != audit.get("proofLedgerTabProofFamilyParity"):
        raise AssertionError(f"coverage index app state audit source proof tab family parity mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerTabProofFamilyFileParity") != audit.get("proofLedgerTabProofFamilyFileParity"):
        raise AssertionError(f"coverage index app state audit source proof tab family file parity mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryCounts") != audit.get("proofCategoryCounts"):
        raise AssertionError(f"coverage index app state audit proof category counts mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategorySurfaces") != audit.get("proofCategorySurfaces"):
        raise AssertionError(f"coverage index app state audit proof surfaces mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategorySurfaceCount") != audit.get("proofCategorySurfaceCount"):
        raise AssertionError(f"coverage index app state audit proof surface count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategoryOtherCount") != audit.get("proofLedgerCategoryOtherCount"):
        raise AssertionError(f"coverage index app state audit source proof other count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategoryTotalCount") != audit.get("proofLedgerCategoryTotalCount"):
        raise AssertionError(f"coverage index app state audit source proof total count mismatch: {app_state_group}")
    if app_state_group.get("auditProofLedgerCategoryParity") != audit.get("proofLedgerCategoryParity"):
        raise AssertionError(f"coverage index app state audit source proof parity mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryTotalCount") != audit.get("proofCategoryTotalCount"):
        raise AssertionError(f"coverage index app state audit proof total count mismatch: {app_state_group}")
    if app_state_group.get("auditProofCategoryParity") != audit.get("proofCategoryParity"):
        raise AssertionError(f"coverage index app state audit proof parity mismatch: {app_state_group}")
    if app_state_group.get("auditQwenMultimodalProofFileParity") != audit.get("qwenMultimodalProofFileParity"):
        raise AssertionError(f"coverage index app state audit qwen proof-file parity mismatch: {app_state_group}")
    if app_state_group.get("currentGapCount", -1) != 1:
        raise AssertionError(f"coverage index app state current gap count mismatch: {app_state_group}")
    if app_state_group.get("gapSource") != gap.get("source"):
        raise AssertionError(f"coverage index app state gap source mismatch: {app_state_group}")
    if app_state_group.get("gapSourceDerived") != gap.get("sourceDerived"):
        raise AssertionError(f"coverage index app state gap source-derived flag mismatch: {app_state_group}")
    if app_state_group.get("gapSourcePathExists") != gap.get("sourcePathExists"):
        raise AssertionError(f"coverage index app state gap source path flag mismatch: {app_state_group}")
    if app_state_group.get("currentGaps") != gap.get("currentGaps"):
        raise AssertionError(f"coverage index app state current gap list mismatch: {app_state_group}")
    if app_state_group.get("nextGap") != gap.get("nextGap"):
        raise AssertionError(f"coverage index app state next gap mismatch: {app_state_group}")
    if app_state_group.get("gapSupportedFamilies") != gap.get("supportedFamilies"):
        raise AssertionError(f"coverage index app state gap supported families mismatch: {app_state_group}")
    if app_state_group.get("unsupportedMultimodalBlocked") != gap.get("unsupportedMultimodalBlocked"):
        raise AssertionError(f"coverage index app state unsupported multimodal block mismatch: {app_state_group}")
    if app_state_group.get("openGapIds") != gap.get("openGapIds"):
        raise AssertionError(f"coverage index app state open gap ids mismatch: {app_state_group}")
    if app_state_group.get("openGapCount") != gap.get("openGapCount"):
        raise AssertionError(f"coverage index app state open gap count mismatch: {app_state_group}")
    if app_state_group.get("gapContracts") != gap.get("gapContracts"):
        raise AssertionError(f"coverage index app state gap contracts mismatch: {app_state_group}")
    if app_state_group.get("gapContractCount") != gap.get("gapContractCount"):
        raise AssertionError(f"coverage index app state gap contract count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalBlockedModelKindCount") != gap.get("qwenMultimodalBlockedModelKindCount"):
        raise AssertionError(f"coverage index app state qwen blocked kind count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalRequiredRuntimeWorkCount") != gap.get("qwenMultimodalRequiredRuntimeWorkCount"):
        raise AssertionError(f"coverage index app state qwen required work count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalProofCount") != gap.get("qwenMultimodalProofCount"):
        raise AssertionError(f"coverage index app state qwen proof count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalProofFileParity") != gap.get("qwenMultimodalProofFileParity"):
        raise AssertionError(f"coverage index app state qwen proof-file parity mismatch: {app_state_group}")
    qwen_gap = (gap.get("gapContracts") or {}).get("qwenMultimodalRuntime") or {}
    if gap.get("qwenMultimodalPromotionReady") != qwen_gap.get("promotionReady"):
        raise AssertionError(f"coverage index source qwen promotion-ready mismatch: {gap}")
    if gap.get("qwenMultimodalPromotionCriteriaCount") != qwen_gap.get("promotionCriteriaCount"):
        raise AssertionError(f"coverage index source qwen promotion criteria count mismatch: {gap}")
    if gap.get("qwenMultimodalMissingPromotionCriteriaIds") != qwen_gap.get("missingPromotionCriteriaIds"):
        raise AssertionError(f"coverage index source qwen missing criteria mismatch: {gap}")
    if gap.get("qwenMultimodalMissingPromotionProofs") != qwen_gap.get("missingPromotionProofs"):
        raise AssertionError(f"coverage index source qwen missing promotion proof mismatch: {gap}")
    if gap.get("qwenMultimodalPromotionProofExistence") != qwen_gap.get("promotionProofExistence"):
        raise AssertionError(f"coverage index source qwen promotion proof existence mismatch: {gap}")
    if gap.get("qwenMultimodalPromotionProofExistenceCount") != qwen_gap.get("promotionProofExistenceCount"):
        raise AssertionError(f"coverage index source qwen promotion proof existence count mismatch: {gap}")
    if gap.get("qwenMultimodalPromotionProofExistenceParity") != qwen_gap.get("promotionProofExistenceParity"):
        raise AssertionError(f"coverage index source qwen promotion proof existence parity mismatch: {gap}")
    if app_state_group.get("qwenMultimodalPromotionReady") != gap.get("qwenMultimodalPromotionReady"):
        raise AssertionError(f"coverage index app state qwen promotion-ready mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionCriteriaCount") != gap.get("qwenMultimodalPromotionCriteriaCount"):
        raise AssertionError(f"coverage index app state qwen promotion criteria count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalMissingPromotionCriteriaIds") != gap.get("qwenMultimodalMissingPromotionCriteriaIds"):
        raise AssertionError(f"coverage index app state qwen missing criteria mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalMissingPromotionProofs") != gap.get("qwenMultimodalMissingPromotionProofs"):
        raise AssertionError(f"coverage index app state qwen missing promotion proof mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionProofExistence") != gap.get("qwenMultimodalPromotionProofExistence"):
        raise AssertionError(f"coverage index app state qwen promotion proof existence mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionProofExistenceCount") != gap.get("qwenMultimodalPromotionProofExistenceCount"):
        raise AssertionError(f"coverage index app state qwen promotion proof existence count mismatch: {app_state_group}")
    if app_state_group.get("qwenMultimodalPromotionProofExistenceParity") != gap.get("qwenMultimodalPromotionProofExistenceParity"):
        raise AssertionError(f"coverage index app state qwen promotion proof existence parity mismatch: {app_state_group}")
    if "qwenMultimodalRuntime" not in (app_state_group.get("openGapIds") or []):
        raise AssertionError(f"coverage index app state missing qwen multimodal gap id: {app_state_group}")
    release_group = groups.get("releaseReadiness") or {}
    release_coverage = request("GET", "/qa/release-readiness")
    beta_readiness = request("GET", "/qa/beta-readiness-coverage")
    if release_group.get("releaseRoute") != "/qa/release-readiness":
        raise AssertionError(f"coverage index release route mismatch: {release_group}")
    if release_group.get("releaseProofs") != release_coverage.get("proofs"):
        raise AssertionError(f"coverage index release proof list mismatch: {release_group}")
    if release_group.get("releaseProofFileParity") != release_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index release proof-file parity mismatch: {release_group}")
    if release_group.get("releaseArtifacts") != release_coverage.get("artifacts"):
        raise AssertionError(f"coverage index release artifact map mismatch: {release_group}")
    if release_group.get("releaseManifestFields") != release_coverage.get("manifestFields"):
        raise AssertionError(f"coverage index release manifest fields mismatch: {release_group}")
    if release_group.get("notarizationGate") != release_coverage.get("notarizationGate"):
        raise AssertionError(f"coverage index release notarization gate mismatch: {release_group}")
    if release_group.get("notarizationGate") not in {"passed", "requires-notary-credentials"}:
        raise AssertionError(f"coverage index release notarization gate is not a known beta gate: {release_group}")
    if release_group.get("notaryProfileRequired") != release_coverage.get("notaryProfileRequired"):
        raise AssertionError(f"coverage index release notary profile requirement mismatch: {release_group}")
    if release_group.get("notarizationGateReason") != release_coverage.get("notarizationGateReason"):
        raise AssertionError(f"coverage index release notarization gate reason mismatch: {release_group}")
    if release_group.get("releaseCommands") != release_coverage.get("commands"):
        raise AssertionError(f"coverage index release command map mismatch: {release_group}")
    if release_group.get("pythonEngine") is not True:
        raise AssertionError(f"coverage index release missing bundled Python engine flag: {release_group}")
    if release_group.get("pythonEngineVenv") is not False:
        raise AssertionError(f"coverage index release should exclude local engine virtualenv: {release_group}")
    if release_group.get("bundledEngineLaunch") is not True or release_group.get("bundledEngineServer") is not True:
        raise AssertionError(f"coverage index release bundled engine file parity mismatch: {release_group}")
    if release_group.get("betaReadinessGates") != beta_readiness.get("gates"):
        raise AssertionError(f"coverage index beta readiness gates mismatch: {release_group}")
    if release_group.get("betaReadinessGateStatus") != beta_readiness.get("gateStatus"):
        raise AssertionError(f"coverage index beta readiness status mismatch: {release_group}")
    if release_group.get("betaReadinessReadyGateCount") != beta_readiness.get("readyGateCount"):
        raise AssertionError(f"coverage index beta readiness ready count mismatch: {release_group}")
    if release_group.get("betaReadinessBlockedGateCount") != beta_readiness.get("blockedGateCount"):
        raise AssertionError(f"coverage index beta readiness blocked count mismatch: {release_group}")
    if release_group.get("betaPackageReady") != beta_readiness.get("packageReady"):
        raise AssertionError(f"coverage index beta package-ready mismatch: {release_group}")
    if release_group.get("betaDistributionReady") != beta_readiness.get("distributionReady"):
        raise AssertionError(f"coverage index beta distribution-ready mismatch: {release_group}")
    if release_group.get("betaReadinessProofs") != beta_readiness.get("proofs"):
        raise AssertionError(f"coverage index beta readiness proof list mismatch: {release_group}")
    if release_group.get("betaReadinessProofFileParity") != beta_readiness.get("proofFileParity"):
        raise AssertionError(f"coverage index beta readiness proof-file parity mismatch: {release_group}")
    runtime_group = groups.get("runtimeAndCache") or {}
    if runtime_group.get("liveProofArtifactCount", 0) < 6:
        raise AssertionError(f"coverage index runtime live artifact count mismatch: {runtime_group}")
    if set(runtime_group.get("supportedFamilies") or []) != {"qwen", "minimax"}:
        raise AssertionError(f"coverage index runtime supported family mismatch: {runtime_group}")
    if runtime_group.get("cacheResponseMethod") != "prefix-cache-l2-turboquant":
        raise AssertionError(f"coverage index runtime cache response method mismatch: {runtime_group}")
    runtime_coverage = request("GET", "/qa/runtime-coverage")
    deep_runtime = request("GET", "/qa/deep-runtime-flow-coverage")
    continuous_batching = request("GET", "/qa/continuous-batching-coverage")
    if runtime_group.get("runtimeContracts") != runtime_coverage.get("contracts"):
        raise AssertionError(f"coverage index runtime contract map mismatch: {runtime_group}")
    if runtime_group.get("runtimeContractCount") != len(runtime_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index runtime contract count mismatch: {runtime_group}")
    if runtime_group.get("runtimeRoutes") != runtime_coverage.get("routes"):
        raise AssertionError(f"coverage index runtime route list mismatch: {runtime_group}")
    if runtime_group.get("runtimeRouteCount") != len(runtime_coverage.get("routes") or []):
        raise AssertionError(f"coverage index runtime route count mismatch: {runtime_group}")
    if runtime_group.get("runtimeProofs") != runtime_coverage.get("proofs"):
        raise AssertionError(f"coverage index runtime proof list mismatch: {runtime_group}")
    if runtime_group.get("runtimeProofCount") != runtime_coverage.get("proofCount"):
        raise AssertionError(f"coverage index runtime proof count mismatch: {runtime_group}")
    if runtime_group.get("runtimeProofFileParity") != runtime_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index runtime proof-file parity mismatch: {runtime_group}")
    if "/qa/deep-runtime-flow-coverage" not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"coverage index runtime group missing deep runtime flow route: {runtime_group}")
    if "deep-runtime-flow-coverage-proof.py" not in (runtime_group.get("proofs") or []):
        raise AssertionError(f"coverage index runtime group missing deep runtime proof: {runtime_group}")
    if "/qa/continuous-batching-coverage" not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"coverage index runtime group missing continuous batching route: {runtime_group}")
    if "continuous-batching-coverage-proof.py" not in (runtime_group.get("proofs") or []):
        raise AssertionError(f"coverage index runtime group missing continuous batching proof: {runtime_group}")
    if "parallel-agent-session-proof.py" not in (runtime_group.get("proofs") or []):
        raise AssertionError(f"coverage index runtime group missing parallel agent proof: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowDomains") != deep_runtime.get("domains"):
        raise AssertionError(f"coverage index deep runtime domains mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowDomainCount") != deep_runtime.get("domainCount"):
        raise AssertionError(f"coverage index deep runtime domain count mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowDomainParity") != deep_runtime.get("domainParity"):
        raise AssertionError(f"coverage index deep runtime domain parity mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowDomainProofFileParity") != deep_runtime.get("domainProofFileParity"):
        raise AssertionError(f"coverage index deep runtime proof-file parity mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowContractParity") != deep_runtime.get("contractParity"):
        raise AssertionError(f"coverage index deep runtime contract parity mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowRouteCount") != deep_runtime.get("routeCount"):
        raise AssertionError(f"coverage index deep runtime route count mismatch: {runtime_group}")
    if runtime_group.get("deepRuntimeFlowProofFileParity") != deep_runtime.get("proofFileParity"):
        raise AssertionError(f"coverage index deep runtime proof parity mismatch: {runtime_group}")
    if continuous_batching.get("ok") is not True:
        raise AssertionError(f"continuous batching coverage route failed: {continuous_batching}")
    if runtime_group.get("continuousBatchingContracts") != continuous_batching.get("contracts"):
        raise AssertionError(f"coverage index continuous batching contract map mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingContractCount") != continuous_batching.get("contractCount"):
        raise AssertionError(f"coverage index continuous batching contract count mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingContractParity") != continuous_batching.get("contractParity"):
        raise AssertionError(f"coverage index continuous batching contract parity mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingProofLevel") != continuous_batching.get("proofLevel"):
        raise AssertionError(f"coverage index continuous batching proof level mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingLiveLoadedModelStress") != continuous_batching.get("liveLoadedModelStress"):
        raise AssertionError(f"coverage index continuous batching live stress label mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingSourceFileParity") != continuous_batching.get("sourceFileParity"):
        raise AssertionError(f"coverage index continuous batching source parity mismatch: {runtime_group}")
    if runtime_group.get("continuousBatchingProofFileParity") != continuous_batching.get("proofFileParity"):
        raise AssertionError(f"coverage index continuous batching proof parity mismatch: {runtime_group}")
    for key in (
        "qwenContinuousBatchingArtifact",
        "qwenContinuousBatchingArtifactOK",
        "qwenContinuousBatchingModel",
        "qwenContinuousBatchingClientOverlap",
        "qwenContinuousBatchingMaxNumSeqs",
        "qwenContinuousBatchingMaxRunningObserved",
        "qwenContinuousBatchingMaxWaitingObserved",
        "qwenContinuousBatchingRequestsProcessed",
        "qwenContinuousBatchingKVBits",
        "qwenContinuousBatchingBlockL2DiskWrites",
        "qwenContinuousBatchingSSMReDeriveCompleted",
        "qwenContinuousBatchingSSMReDeriveFailed",
        "qwenContinuousBatchingMemoryActiveMB",
    ):
        if runtime_group.get(key) != continuous_batching.get(key):
            raise AssertionError(f"coverage index continuous batching {key} mismatch: {runtime_group}")
    python_runtime = request("GET", "/qa/python-runtime-inventory")
    engine_python_runtime = request("GET", "/qa/engine-python-runtime")
    if python_runtime.get("ok") is not True:
        raise AssertionError(f"python runtime inventory route failed: {python_runtime}")
    if python_runtime.get("parseParity") is not True:
        raise AssertionError(f"python runtime inventory parse parity mismatch: {python_runtime}")
    if python_runtime.get("functionCount", 0) < 500:
        raise AssertionError(f"python runtime inventory function count too low: {python_runtime}")
    if python_runtime.get("proofFileParity") is not True:
        raise AssertionError(f"python runtime inventory proof-file parity mismatch: {python_runtime}")
    if runtime_group.get("pythonRuntimeInventoryFileCount") != python_runtime.get("fileCount"):
        raise AssertionError(f"coverage index python runtime file count mismatch: {runtime_group}")
    if runtime_group.get("pythonRuntimeInventoryFunctionCount") != python_runtime.get("functionCount"):
        raise AssertionError(f"coverage index python runtime function count mismatch: {runtime_group}")
    if runtime_group.get("pythonRuntimeInventoryGroupCounts") != python_runtime.get("groupCounts"):
        raise AssertionError(f"coverage index python runtime group counts mismatch: {runtime_group}")
    if runtime_group.get("pythonRuntimeInventoryProofFileParity") != python_runtime.get("proofFileParity"):
        raise AssertionError(f"coverage index python runtime proof parity mismatch: {runtime_group}")
    if engine_python_runtime.get("ok") is not True:
        raise AssertionError(f"engine python runtime route failed: {engine_python_runtime}")
    selected_engine_python = engine_python_runtime.get("selected") or {}
    if selected_engine_python.get("valid") is not True or selected_engine_python.get("missingModuleCount") != 0:
        raise AssertionError(f"engine python runtime selected runtime invalid: {engine_python_runtime}")
    if "/qa/engine-python-runtime" not in (runtime_group.get("endpoints") or []):
        raise AssertionError(f"coverage index runtime group missing engine python route: {runtime_group}")
    if runtime_group.get("liveProofs") != runtime_coverage.get("liveProofs"):
        raise AssertionError(f"coverage index runtime live proof matrix mismatch: {runtime_group}")
    if runtime_group.get("liveProofArtifacts") != runtime_coverage.get("liveProofArtifacts"):
        raise AssertionError(f"coverage index runtime live proof artifact map mismatch: {runtime_group}")
    if runtime_coverage.get("liveProofArtifactFileParity") is not True:
        raise AssertionError(f"runtime coverage live proof artifact file parity mismatch: {runtime_coverage}")
    if runtime_group.get("liveProofArtifactFileParity") != runtime_coverage.get("liveProofArtifactFileParity"):
        raise AssertionError(f"coverage index runtime live proof artifact file parity mismatch: {runtime_group}")
    for key in (
        "qwenSSMReDeriveArtifact",
        "qwenSSMReDeriveArtifactOK",
        "qwenSSMReDeriveRequested",
        "qwenSSMReDeriveCompleted",
        "qwenSSMReDeriveNoFailures",
        "qwenSSMReDeriveLastNumTokens",
        "qwenContinuousBatchingArtifact",
        "qwenContinuousBatchingArtifactOK",
        "qwenContinuousBatchingMaxRunningObserved",
        "qwenContinuousBatchingRequestsProcessed",
        "qwenContinuousBatchingKVBits",
    ):
        if runtime_group.get(key) != runtime_coverage.get(key):
            raise AssertionError(f"coverage index runtime {key} mismatch: {runtime_group}")
    for key, runtime_key in (
        ("runtimeQwenContinuousBatchingArtifactOK", "qwenContinuousBatchingArtifactOK"),
        ("runtimeQwenContinuousBatchingMaxRunningObserved", "qwenContinuousBatchingMaxRunningObserved"),
    ):
        if runtime_group.get(key) != runtime_coverage.get(runtime_key):
            raise AssertionError(f"coverage index runtime {key} mismatch: {runtime_group}")
    if runtime_group.get("cacheResponsesInferenceMethod") != runtime_coverage.get("cacheResponsesInferenceMethod"):
        raise AssertionError(f"coverage index runtime cache responses inference method mismatch: {runtime_group}")
    if runtime_group.get("newModelSessionBehavior") != runtime_coverage.get("newModelSessionBehavior"):
        raise AssertionError(f"coverage index runtime new model session behavior mismatch: {runtime_group}")
    if runtime_group.get("cacheComponents") != runtime_coverage.get("cacheComponents"):
        raise AssertionError(f"coverage index runtime cache components mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentCount") != runtime_coverage.get("cacheComponentCount"):
        raise AssertionError(f"coverage index runtime cache component count mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentParity") != runtime_coverage.get("cacheComponentParity"):
        raise AssertionError(f"coverage index runtime cache component parity mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentProofs") != runtime_coverage.get("cacheComponentProofs"):
        raise AssertionError(f"coverage index runtime cache component proof map mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentProofCount") != runtime_coverage.get("cacheComponentProofCount"):
        raise AssertionError(f"coverage index runtime cache component proof count mismatch: {runtime_group}")
    if runtime_group.get("cacheComponentProofParity") != runtime_coverage.get("cacheComponentProofParity"):
        raise AssertionError(f"coverage index runtime cache component proof parity mismatch: {runtime_group}")
    if runtime_coverage.get("cacheComponentProofFileParity") is not True:
        raise AssertionError(f"runtime coverage cache component proof-file parity mismatch: {runtime_coverage}")
    if runtime_group.get("cacheComponentProofFileParity") != runtime_coverage.get("cacheComponentProofFileParity"):
        raise AssertionError(f"coverage index runtime cache component proof-file parity mismatch: {runtime_group}")
    chat_context_group = groups.get("chatAndContext") or {}
    chat_coverage = request("GET", "/qa/chat-coverage")
    if chat_context_group.get("stateKeyCount", 0) < 19:
        raise AssertionError(f"coverage index chat/context state key count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadges") != chat_coverage.get("headerCacheBadges"):
        raise AssertionError(f"coverage index chat/context header cache badges mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeCount") != chat_coverage.get("headerCacheBadgeCount"):
        raise AssertionError(f"coverage index chat/context header cache badge count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeParity") != chat_coverage.get("headerCacheBadgeParity"):
        raise AssertionError(f"coverage index chat/context header cache badge parity mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeProofs") != chat_coverage.get("headerCacheBadgeProofs"):
        raise AssertionError(f"coverage index chat/context header cache badge proof map mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeProofCount") != chat_coverage.get("headerCacheBadgeProofCount"):
        raise AssertionError(f"coverage index chat/context header cache badge proof count mismatch: {chat_context_group}")
    if chat_context_group.get("headerCacheBadgeProofParity") != chat_coverage.get("headerCacheBadgeProofParity"):
        raise AssertionError(f"coverage index chat/context header cache badge proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionIndicator") != chat_coverage.get("cacheSessionIndicator"):
        raise AssertionError(f"coverage index chat/context cache session indicator mismatch: {chat_context_group}")
    if chat_context_group.get("cacheResponsesInferenceMethod") != chat_coverage.get("cacheResponsesInferenceMethod"):
        raise AssertionError(f"coverage index chat/context cache responses inference method mismatch: {chat_context_group}")
    if chat_context_group.get("newModelSessionBehavior") != chat_coverage.get("newModelSessionBehavior"):
        raise AssertionError(f"coverage index chat/context new model session behavior mismatch: {chat_context_group}")
    if chat_context_group.get("newContextSessionBoundary") != chat_coverage.get("newContextSessionBoundary"):
        raise AssertionError(f"coverage index chat/context new context boundary mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFields") != chat_coverage.get("cacheSessionFields"):
        raise AssertionError(f"coverage index chat/context cache session fields mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldCount") != chat_coverage.get("cacheSessionFieldCount"):
        raise AssertionError(f"coverage index chat/context cache session field count mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldParity") != chat_coverage.get("cacheSessionFieldParity"):
        raise AssertionError(f"coverage index chat/context cache session field parity mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldProofs") != chat_coverage.get("cacheSessionFieldProofs"):
        raise AssertionError(f"coverage index chat/context cache session field proof map mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldProofCount") != chat_coverage.get("cacheSessionFieldProofCount"):
        raise AssertionError(f"coverage index chat/context cache session field proof count mismatch: {chat_context_group}")
    if chat_context_group.get("cacheSessionFieldProofParity") != chat_coverage.get("cacheSessionFieldProofParity"):
        raise AssertionError(f"coverage index chat/context cache session field proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("chatRoutes") != chat_coverage.get("routes"):
        raise AssertionError(f"coverage index chat/context chat route list mismatch: {chat_context_group}")
    if chat_context_group.get("chatRouteCount") != len(chat_coverage.get("routes") or []):
        raise AssertionError(f"coverage index chat/context chat route count mismatch: {chat_context_group}")
    if chat_context_group.get("chatContracts") != chat_coverage.get("contracts"):
        raise AssertionError(f"coverage index chat/context chat contract map mismatch: {chat_context_group}")
    if chat_context_group.get("chatContractCount") != len(chat_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index chat/context chat contract count mismatch: {chat_context_group}")
    if chat_context_group.get("chatProofs") != chat_coverage.get("proofs"):
        raise AssertionError(f"coverage index chat/context chat proof list mismatch: {chat_context_group}")
    if chat_context_group.get("chatProofCount") != chat_coverage.get("proofCount"):
        raise AssertionError(f"coverage index chat/context chat proof count mismatch: {chat_context_group}")
    if chat_context_group.get("chatProofFileParity") != chat_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index chat/context chat proof-file parity mismatch: {chat_context_group}")
    if chat_context_group.get("chatStateKeys") != chat_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index chat/context chat state-key list mismatch: {chat_context_group}")
    if chat_context_group.get("chatStateKeyCount") != len(chat_coverage.get("stateKeys") or []):
        raise AssertionError(f"coverage index chat/context chat state-key count mismatch: {chat_context_group}")
    context_coverage = request("GET", "/qa/context-coverage")
    if chat_context_group.get("searchToolName") != context_coverage.get("searchToolName"):
        raise AssertionError(f"coverage index chat/context search tool mismatch: {chat_context_group}")
    if chat_context_group.get("automaticInjectedContextCap") != context_coverage.get("automaticInjectedContextCap"):
        raise AssertionError(f"coverage index chat/context automatic context cap mismatch: {chat_context_group}")
    if chat_context_group.get("currentInjectedContextLimit") != context_coverage.get("currentInjectedContextLimit"):
        raise AssertionError(f"coverage index chat/context current context limit mismatch: {chat_context_group}")
    if chat_context_group.get("contextRoutes") != context_coverage.get("routes"):
        raise AssertionError(f"coverage index chat/context context route list mismatch: {chat_context_group}")
    if chat_context_group.get("contextRouteCount") != len(context_coverage.get("routes") or []):
        raise AssertionError(f"coverage index chat/context context route count mismatch: {chat_context_group}")
    if chat_context_group.get("contextContracts") != context_coverage.get("contracts"):
        raise AssertionError(f"coverage index chat/context context contract map mismatch: {chat_context_group}")
    if chat_context_group.get("contextContractCount") != len(context_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index chat/context context contract count mismatch: {chat_context_group}")
    if chat_context_group.get("contextProofs") != context_coverage.get("proofs"):
        raise AssertionError(f"coverage index chat/context context proof list mismatch: {chat_context_group}")
    if chat_context_group.get("contextProofCount") != context_coverage.get("proofCount"):
        raise AssertionError(f"coverage index chat/context context proof count mismatch: {chat_context_group}")
    if chat_context_group.get("contextProofFileParity") != context_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index chat/context context proof-file parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextStateKeys") != context_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index chat/context context state-key list mismatch: {chat_context_group}")
    if chat_context_group.get("contextStateKeyCount") != len(context_coverage.get("stateKeys") or []):
        raise AssertionError(f"coverage index chat/context context state-key count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSources") != context_coverage.get("retrievalSources"):
        raise AssertionError(f"coverage index chat/context retrieval sources mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceCount") != context_coverage.get("retrievalSourceCount"):
        raise AssertionError(f"coverage index chat/context retrieval source count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceParity") != context_coverage.get("retrievalSourceParity"):
        raise AssertionError(f"coverage index chat/context retrieval source parity mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofs") != context_coverage.get("retrievalSourceProofs"):
        raise AssertionError(f"coverage index chat/context retrieval source proof map mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofCount") != context_coverage.get("retrievalSourceProofCount"):
        raise AssertionError(f"coverage index chat/context retrieval source proof count mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofParity") != context_coverage.get("retrievalSourceProofParity"):
        raise AssertionError(f"coverage index chat/context retrieval source proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("retrievalSourceProofFileParity") != context_coverage.get("retrievalSourceProofFileParity"):
        raise AssertionError(f"coverage index chat/context retrieval source proof-file parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModes") != context_coverage.get("contextDeliveryModes"):
        raise AssertionError(f"coverage index chat/context delivery modes mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeCount") != context_coverage.get("contextDeliveryModeCount"):
        raise AssertionError(f"coverage index chat/context delivery mode count mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeParity") != context_coverage.get("contextDeliveryModeParity"):
        raise AssertionError(f"coverage index chat/context delivery mode parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofs") != context_coverage.get("contextDeliveryModeProofs"):
        raise AssertionError(f"coverage index chat/context delivery mode proof map mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofCount") != context_coverage.get("contextDeliveryModeProofCount"):
        raise AssertionError(f"coverage index chat/context delivery mode proof count mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofParity") != context_coverage.get("contextDeliveryModeProofParity"):
        raise AssertionError(f"coverage index chat/context delivery mode proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextDeliveryModeProofFileParity") != context_coverage.get("contextDeliveryModeProofFileParity"):
        raise AssertionError(f"coverage index chat/context delivery mode proof-file parity mismatch: {chat_context_group}")
    context_flow_matrix = request("GET", "/qa/context-flow-matrix")
    if context_flow_matrix.get("ok") is not True:
        raise AssertionError(f"context flow matrix route failed: {context_flow_matrix}")
    if context_flow_matrix.get("retrievalSourceCount") != context_coverage.get("retrievalSourceCount"):
        raise AssertionError(f"context flow matrix retrieval source count mismatch: {context_flow_matrix}")
    if context_flow_matrix.get("deliveryModeCount") != context_coverage.get("contextDeliveryModeCount"):
        raise AssertionError(f"context flow matrix delivery mode count mismatch: {context_flow_matrix}")
    if context_flow_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"context flow matrix proof owner parity mismatch: {context_flow_matrix}")
    if context_flow_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"context flow matrix proof-file parity mismatch: {context_flow_matrix}")
    if chat_context_group.get("contextFlowMatrixRetrievalSourceCount") != context_flow_matrix.get("retrievalSourceCount"):
        raise AssertionError(f"coverage index context flow matrix retrieval count mismatch: {chat_context_group}")
    if chat_context_group.get("contextFlowMatrixDeliveryModeCount") != context_flow_matrix.get("deliveryModeCount"):
        raise AssertionError(f"coverage index context flow matrix delivery count mismatch: {chat_context_group}")
    if chat_context_group.get("contextFlowMatrixProofOwnerFileParity") != context_flow_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index context flow matrix owner parity mismatch: {chat_context_group}")
    if chat_context_group.get("contextFlowMatrixProofFileParity") != context_flow_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index context flow matrix proof parity mismatch: {chat_context_group}")
    agent_flow_inventory = request("GET", "/qa/agent-flow-inventory")
    if agent_flow_inventory.get("ok") is not True:
        raise AssertionError(f"agent flow inventory route failed: {agent_flow_inventory}")
    if agent_flow_inventory.get("fileCount", 0) < 8:
        raise AssertionError(f"agent flow inventory file count too low: {agent_flow_inventory}")
    if agent_flow_inventory.get("functionCount", 0) < 100:
        raise AssertionError(f"agent flow inventory function count too low: {agent_flow_inventory}")
    if agent_flow_inventory.get("phaseCoverageParity") is not True:
        raise AssertionError(f"agent flow inventory phase parity mismatch: {agent_flow_inventory}")
    if agent_flow_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"agent flow inventory proof-file parity mismatch: {agent_flow_inventory}")
    if chat_context_group.get("agentFlowInventoryFileCount") != agent_flow_inventory.get("fileCount"):
        raise AssertionError(f"coverage index agent flow file count mismatch: {chat_context_group}")
    if chat_context_group.get("agentFlowInventoryFunctionCount") != agent_flow_inventory.get("functionCount"):
        raise AssertionError(f"coverage index agent flow function count mismatch: {chat_context_group}")
    if chat_context_group.get("agentFlowInventoryGroupCounts") != agent_flow_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index agent flow group counts mismatch: {chat_context_group}")
    if chat_context_group.get("agentFlowInventoryPhaseCoverageParity") != agent_flow_inventory.get("phaseCoverageParity"):
        raise AssertionError(f"coverage index agent flow phase parity mismatch: {chat_context_group}")
    if chat_context_group.get("agentFlowInventoryProofFileParity") != agent_flow_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index agent flow proof parity mismatch: {chat_context_group}")
    evidence_lifecycle = request("GET", "/qa/evidence-lifecycle-coverage")
    if chat_context_group.get("evidenceLifecycleStages") != evidence_lifecycle.get("stages"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle stages mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleStageCount") != evidence_lifecycle.get("stageCount"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle stage count mismatch: {chat_context_group}")
    if evidence_lifecycle.get("stageParity") is not True:
        raise AssertionError(f"evidence lifecycle stage parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleStageParity") != evidence_lifecycle.get("stageParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle stage parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleStorageTargets") != evidence_lifecycle.get("storageTargets"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle storage targets mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleStorageTargetCount") != evidence_lifecycle.get("storageTargetCount"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle storage target count mismatch: {chat_context_group}")
    if evidence_lifecycle.get("storageTargetParity") is not True:
        raise AssertionError(f"evidence lifecycle storage target parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleStorageTargetParity") != evidence_lifecycle.get("storageTargetParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle storage target parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleHandoffs") != evidence_lifecycle.get("handoffs"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle handoffs mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleHandoffCount") != evidence_lifecycle.get("handoffCount"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle handoff count mismatch: {chat_context_group}")
    if evidence_lifecycle.get("handoffParity") is not True:
        raise AssertionError(f"evidence lifecycle handoff parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleHandoffParity") != evidence_lifecycle.get("handoffParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle handoff parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleRoutes") != evidence_lifecycle.get("routes"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle routes mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleRouteCount") != evidence_lifecycle.get("routeCount"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle route count mismatch: {chat_context_group}")
    if evidence_lifecycle.get("routeParity") is not True:
        raise AssertionError(f"evidence lifecycle route parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleRouteParity") != evidence_lifecycle.get("routeParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle route parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleProofs") != evidence_lifecycle.get("proofs"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle proofs mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleProofCount") != evidence_lifecycle.get("proofCount"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle proof count mismatch: {chat_context_group}")
    if evidence_lifecycle.get("proofFileParity") is not True:
        raise AssertionError(f"evidence lifecycle proof-file parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleProofFileParity") != evidence_lifecycle.get("proofFileParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle proof-file parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleContextPolicy") != evidence_lifecycle.get("contextPolicy"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle context policy mismatch: {chat_context_group}")
    if evidence_lifecycle.get("contextPolicyParity") is not True:
        raise AssertionError(f"evidence lifecycle context policy parity mismatch: {evidence_lifecycle}")
    if chat_context_group.get("evidenceLifecycleContextPolicyParity") != evidence_lifecycle.get("contextPolicyParity"):
        raise AssertionError(f"coverage index chat/context evidence lifecycle context policy parity mismatch: {chat_context_group}")
    evidence_lifecycle_flow_matrix = request("GET", "/qa/evidence-lifecycle-flow-matrix")
    if evidence_lifecycle_flow_matrix.get("ok") is not True:
        raise AssertionError(f"evidence lifecycle flow matrix route failed: {evidence_lifecycle_flow_matrix}")
    if evidence_lifecycle_flow_matrix.get("stageCount") != evidence_lifecycle.get("stageCount"):
        raise AssertionError(f"evidence lifecycle flow matrix stage count mismatch: {evidence_lifecycle_flow_matrix}")
    if evidence_lifecycle_flow_matrix.get("storageTargetCount") != evidence_lifecycle.get("storageTargetCount"):
        raise AssertionError(f"evidence lifecycle flow matrix storage target count mismatch: {evidence_lifecycle_flow_matrix}")
    if evidence_lifecycle_flow_matrix.get("handoffCount") != evidence_lifecycle.get("handoffCount"):
        raise AssertionError(f"evidence lifecycle flow matrix handoff count mismatch: {evidence_lifecycle_flow_matrix}")
    if evidence_lifecycle_flow_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"evidence lifecycle flow matrix owner parity mismatch: {evidence_lifecycle_flow_matrix}")
    if evidence_lifecycle_flow_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"evidence lifecycle flow matrix proof-file parity mismatch: {evidence_lifecycle_flow_matrix}")
    if chat_context_group.get("evidenceLifecycleFlowMatrixStageCount") != evidence_lifecycle_flow_matrix.get("stageCount"):
        raise AssertionError(f"coverage index evidence lifecycle flow matrix stage count mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleFlowMatrixStorageTargetCount") != evidence_lifecycle_flow_matrix.get("storageTargetCount"):
        raise AssertionError(f"coverage index evidence lifecycle flow matrix storage target count mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleFlowMatrixHandoffCount") != evidence_lifecycle_flow_matrix.get("handoffCount"):
        raise AssertionError(f"coverage index evidence lifecycle flow matrix handoff count mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleFlowMatrixProofOwnerFileParity") != evidence_lifecycle_flow_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index evidence lifecycle flow matrix owner parity mismatch: {chat_context_group}")
    if chat_context_group.get("evidenceLifecycleFlowMatrixProofFileParity") != evidence_lifecycle_flow_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index evidence lifecycle flow matrix proof-file parity mismatch: {chat_context_group}")
    cve_taxonomy = request("GET", "/qa/cve-taxonomy-coverage")
    cve_taxonomy_matrix = request("GET", "/qa/cve-taxonomy-matrix")
    if chat_context_group.get("cveTaxonomySourceFeeds") != cve_taxonomy.get("sourceFeeds"):
        raise AssertionError(f"coverage index chat/context cve taxonomy source feed mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomySourceFeedCount") != cve_taxonomy.get("sourceFeedCount"):
        raise AssertionError(f"coverage index chat/context cve taxonomy source feed count mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomySourceFeedParity") != cve_taxonomy.get("sourceFeedParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy source feed parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomySoftwareFamilies") != cve_taxonomy.get("softwareFamilies"):
        raise AssertionError(f"coverage index chat/context cve taxonomy software families mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomySoftwareFamilyCount") != cve_taxonomy.get("softwareFamilyCount"):
        raise AssertionError(f"coverage index chat/context cve taxonomy software family count mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomySoftwareFamilyParity") != cve_taxonomy.get("softwareFamilyParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy software family parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyVulnerabilityClasses") != cve_taxonomy.get("vulnerabilityClasses"):
        raise AssertionError(f"coverage index chat/context cve taxonomy vulnerability classes mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyVulnerabilityClassCount") != cve_taxonomy.get("vulnerabilityClassCount"):
        raise AssertionError(f"coverage index chat/context cve taxonomy vulnerability class count mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyVulnerabilityClassParity") != cve_taxonomy.get("vulnerabilityClassParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy vulnerability class parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyRiskSignals") != cve_taxonomy.get("riskSignals"):
        raise AssertionError(f"coverage index chat/context cve taxonomy risk signals mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyRiskSignalParity") != cve_taxonomy.get("riskSignalParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy risk signal parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyEvidenceFlow") != cve_taxonomy.get("evidenceFlow"):
        raise AssertionError(f"coverage index chat/context cve taxonomy evidence flow mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyEvidenceFlowParity") != cve_taxonomy.get("evidenceFlowParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy evidence flow parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyAgentToolNames") != cve_taxonomy.get("agentToolNames"):
        raise AssertionError(f"coverage index chat/context cve taxonomy tool names mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyBoundedContextContract") != cve_taxonomy.get("boundedContextContract"):
        raise AssertionError(f"coverage index chat/context cve taxonomy context contract mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyReportingContract") != cve_taxonomy.get("reportingContract"):
        raise AssertionError(f"coverage index chat/context cve taxonomy reporting contract mismatch: {chat_context_group}")
    if cve_taxonomy_matrix.get("ok") is not True:
        raise AssertionError(f"cve taxonomy matrix route failed: {cve_taxonomy_matrix}")
    if chat_context_group.get("cveTaxonomyMatrixCount") != cve_taxonomy_matrix.get("totalRowCount"):
        raise AssertionError(f"coverage index chat/context cve taxonomy matrix count mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyMatrixProofFileParity") != cve_taxonomy_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy matrix proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyMatrixRowProofFileParity") != cve_taxonomy_matrix.get("rowProofFileParity"):
        raise AssertionError(f"coverage index chat/context cve taxonomy matrix row proof parity mismatch: {chat_context_group}")
    if chat_context_group.get("cveTaxonomyMatrixEvidenceFlowCount") != cve_taxonomy_matrix.get("evidenceFlowCount"):
        raise AssertionError(f"coverage index chat/context cve taxonomy matrix evidence count mismatch: {chat_context_group}")
    settings_visuals_group = groups.get("settingsAndVisuals") or {}
    settings_coverage = request("GET", "/qa/settings-coverage")
    settings_surface_matrix = request("GET", "/qa/settings-surface-matrix")
    if settings_visuals_group.get("settingsSurfaces") != settings_coverage.get("settingsSurfaces"):
        raise AssertionError(f"coverage index settings surface list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceCount") != settings_coverage.get("settingsSurfaceCount"):
        raise AssertionError(f"coverage index settings surface count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceParity") != settings_coverage.get("settingsSurfaceParity"):
        raise AssertionError(f"coverage index settings surface parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofs") != settings_coverage.get("settingsSurfaceProofs"):
        raise AssertionError(f"coverage index settings surface proof map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofCount") != settings_coverage.get("settingsSurfaceProofCount"):
        raise AssertionError(f"coverage index settings surface proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofParity") != settings_coverage.get("settingsSurfaceProofParity"):
        raise AssertionError(f"coverage index settings surface proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceProofFileParity") != settings_coverage.get("settingsSurfaceProofFileParity"):
        raise AssertionError(f"coverage index settings surface proof-file parity mismatch: {settings_visuals_group}")
    if settings_surface_matrix.get("ok") is not True:
        raise AssertionError(f"settings surface matrix route failed: {settings_surface_matrix}")
    if settings_visuals_group.get("settingsSurfaceMatrixCount") != settings_surface_matrix.get("surfaceCount"):
        raise AssertionError(f"coverage index settings surface matrix count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceMatrixProofFileParity") != settings_surface_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index settings surface matrix proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceMatrixSurfaceProofFileParity") != settings_surface_matrix.get("surfaceProofFileParity"):
        raise AssertionError(f"coverage index settings surface matrix surface proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsSurfaceMatrixThemeFileCount") != settings_surface_matrix.get("themeInventoryFileCount"):
        raise AssertionError(f"coverage index settings surface matrix theme count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCategories") != settings_coverage.get("categories"):
        raise AssertionError(f"coverage index settings category list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCategoryIDs") != settings_coverage.get("categoryIDs"):
        raise AssertionError(f"coverage index settings category id list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCategoryCount") != settings_coverage.get("categoryCount"):
        raise AssertionError(f"coverage index settings category count mismatch: {settings_visuals_group}")
    if settings_coverage.get("categoryParity") is not True:
        raise AssertionError(f"settings coverage category parity mismatch: {settings_coverage}")
    if settings_visuals_group.get("settingsCategoryParity") != settings_coverage.get("categoryParity"):
        raise AssertionError(f"coverage index settings category parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsCurrentCategory") != settings_coverage.get("currentCategory"):
        raise AssertionError(f"coverage index settings current category mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsRoutes") != settings_coverage.get("routes"):
        raise AssertionError(f"coverage index settings route list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsRouteCount") != len(settings_coverage.get("routes") or []):
        raise AssertionError(f"coverage index settings route count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsContracts") != settings_coverage.get("contracts"):
        raise AssertionError(f"coverage index settings contract map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsContractCount") != len(settings_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index settings contract count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsProofs") != settings_coverage.get("proofs"):
        raise AssertionError(f"coverage index settings proof list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsProofCount") != settings_coverage.get("proofCount"):
        raise AssertionError(f"coverage index settings proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsProofFileParity") != settings_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index settings proof-file parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsVisualManifests") != settings_coverage.get("visualManifests"):
        raise AssertionError(f"coverage index settings visual manifest list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("settingsVisualManifestCount", 0) < 6:
        raise AssertionError(f"coverage index settings visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualManifestCount", 0) < 22:
        raise AssertionError(f"coverage index visual manifest count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("actualCaptureCount", 0) < 48:
        raise AssertionError(f"coverage index visual capture count mismatch: {settings_visuals_group}")
    visual_coverage = request("GET", "/qa/visual-coverage")
    if settings_visuals_group.get("visualRoutes") != visual_coverage.get("routes"):
        raise AssertionError(f"coverage index visual route list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualRouteCount") != len(visual_coverage.get("routes") or []):
        raise AssertionError(f"coverage index visual route count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualContracts") != visual_coverage.get("contracts"):
        raise AssertionError(f"coverage index visual contract map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualContractCount") != len(visual_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index visual contract count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualProofs") != visual_coverage.get("proofs"):
        raise AssertionError(f"coverage index visual proof list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualProofCount") != visual_coverage.get("proofCount"):
        raise AssertionError(f"coverage index visual proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualProofFileParity") != visual_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index visual proof-file parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualManifests") != visual_coverage.get("manifests"):
        raise AssertionError(f"coverage index visual manifest list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("minimumCaptureCount") != visual_coverage.get("minimumCaptureCount"):
        raise AssertionError(f"coverage index visual minimum capture count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaces") != visual_coverage.get("visualSurfaces"):
        raise AssertionError(f"coverage index visual surface list mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceCount") != visual_coverage.get("visualSurfaceCount"):
        raise AssertionError(f"coverage index visual surface count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceParity") != visual_coverage.get("visualSurfaceParity"):
        raise AssertionError(f"coverage index visual surface parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofs") != visual_coverage.get("visualSurfaceProofs"):
        raise AssertionError(f"coverage index visual surface proof map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofCount") != visual_coverage.get("visualSurfaceProofCount"):
        raise AssertionError(f"coverage index visual surface proof count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofParity") != visual_coverage.get("visualSurfaceProofParity"):
        raise AssertionError(f"coverage index visual surface proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceProofFileParity") != visual_coverage.get("visualSurfaceProofFileParity"):
        raise AssertionError(f"coverage index visual surface proof-file parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualTabProofFamilies") != visual_coverage.get("visualTabProofFamilies"):
        raise AssertionError(f"coverage index visual tab family map mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualTabProofFamilyCount") != visual_coverage.get("visualTabProofFamilyCount"):
        raise AssertionError(f"coverage index visual tab family count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualTabProofFamilyParity") != visual_coverage.get("visualTabProofFamilyParity"):
        raise AssertionError(f"coverage index visual tab family parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualTabProofFamilyFileParity") != visual_coverage.get("visualTabProofFamilyFileParity"):
        raise AssertionError(f"coverage index visual tab family file parity mismatch: {settings_visuals_group}")
    visual_surface_matrix = request("GET", "/qa/visual-surface-matrix")
    if visual_surface_matrix.get("ok") is not True:
        raise AssertionError(f"visual surface matrix route failed: {visual_surface_matrix}")
    if visual_surface_matrix.get("surfaceCount") != visual_coverage.get("visualSurfaceCount"):
        raise AssertionError(f"visual surface matrix count mismatch: {visual_surface_matrix}")
    if visual_surface_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"visual surface matrix owner parity mismatch: {visual_surface_matrix}")
    if visual_surface_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"visual surface matrix proof-file parity mismatch: {visual_surface_matrix}")
    if visual_surface_matrix.get("manifestCount") != visual_coverage.get("manifestCount"):
        raise AssertionError(f"visual surface matrix manifest count mismatch: {visual_surface_matrix}")
    if settings_visuals_group.get("visualSurfaceMatrixCount") != visual_surface_matrix.get("surfaceCount"):
        raise AssertionError(f"coverage index visual surface matrix count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceMatrixProofOwnerFileParity") != visual_surface_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index visual surface matrix owner parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceMatrixProofFileParity") != visual_surface_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index visual surface matrix proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("visualSurfaceMatrixManifestCount") != visual_surface_matrix.get("manifestCount"):
        raise AssertionError(f"coverage index visual surface matrix manifest count mismatch: {settings_visuals_group}")
    theme_inventory = request("GET", "/qa/theme-inventory")
    if theme_inventory.get("ok") is not True:
        raise AssertionError(f"theme inventory route failed: {theme_inventory}")
    if theme_inventory.get("fileCount", 0) < 8:
        raise AssertionError(f"theme inventory file count too low: {theme_inventory}")
    if theme_inventory.get("staticTokenCount", 0) < 20:
        raise AssertionError(f"theme inventory static token count too low: {theme_inventory}")
    if theme_inventory.get("professionalShapePolicy") != "max-corner-radius-8":
        raise AssertionError(f"theme inventory shape policy mismatch: {theme_inventory}")
    if theme_inventory.get("maxCornerRadius", 0) > 8:
        raise AssertionError(f"theme inventory corner radius policy mismatch: {theme_inventory}")
    if theme_inventory.get("proofFileParity") is not True:
        raise AssertionError(f"theme inventory proof-file parity mismatch: {theme_inventory}")
    if settings_visuals_group.get("themeInventoryFileCount") != theme_inventory.get("fileCount"):
        raise AssertionError(f"coverage index theme inventory file count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeInventoryTypeCount") != theme_inventory.get("typeCount"):
        raise AssertionError(f"coverage index theme inventory type count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeInventoryStaticTokenCount") != theme_inventory.get("staticTokenCount"):
        raise AssertionError(f"coverage index theme inventory static token count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeInventoryGroupCounts") != theme_inventory.get("groupCounts"):
        raise AssertionError(f"coverage index theme inventory group counts mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeInventoryProofFileParity") != theme_inventory.get("proofFileParity"):
        raise AssertionError(f"coverage index theme inventory proof parity mismatch: {settings_visuals_group}")
    theme_token_matrix = request("GET", "/qa/theme-token-matrix")
    if theme_token_matrix.get("ok") is not True:
        raise AssertionError(f"theme token matrix route failed: {theme_token_matrix}")
    if theme_token_matrix.get("fileCount") != theme_inventory.get("fileCount"):
        raise AssertionError(f"theme token matrix file count mismatch: {theme_token_matrix}")
    if theme_token_matrix.get("staticTokenCount") != theme_inventory.get("staticTokenCount"):
        raise AssertionError(f"theme token matrix static token count mismatch: {theme_token_matrix}")
    if theme_token_matrix.get("policyParity") is not True:
        raise AssertionError(f"theme token matrix policy parity mismatch: {theme_token_matrix}")
    if settings_visuals_group.get("themeTokenMatrixFileCount") != theme_token_matrix.get("fileCount"):
        raise AssertionError(f"coverage index theme token matrix file count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeTokenMatrixStaticTokenCount") != theme_token_matrix.get("staticTokenCount"):
        raise AssertionError(f"coverage index theme token matrix static count mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeTokenMatrixProofFileParity") != theme_token_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index theme token matrix proof parity mismatch: {settings_visuals_group}")
    if settings_visuals_group.get("themeTokenMatrixPolicyParity") != theme_token_matrix.get("policyParity"):
        raise AssertionError(f"coverage index theme token matrix policy parity mismatch: {settings_visuals_group}")
    tools_parsers_group = groups.get("toolsAndParsers") or {}
    if tools_parsers_group.get("toolCount", 0) < 38:
        raise AssertionError(f"coverage index tools/parsers tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("callbackCount", 0) < 3:
        raise AssertionError(f"coverage index tools/parsers callback count mismatch: {tools_parsers_group}")
    tool_coverage = request("GET", "/qa/tool-coverage")
    if tools_parsers_group.get("toolRegistryTools") != tool_coverage.get("tools"):
        raise AssertionError(f"coverage index tools/parsers tool registry list mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryTabs") != tool_coverage.get("tabs"):
        raise AssertionError(f"coverage index tools/parsers tool registry tab list mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryFailures") != tool_coverage.get("failures"):
        raise AssertionError(f"coverage index tools/parsers tool registry failures mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolRegistryFailureCount") != len(tool_coverage.get("failures") or []):
        raise AssertionError(f"coverage index tools/parsers tool registry failure count mismatch: {tools_parsers_group}")
    for key in (
        "tabToolMap",
        "tabToolCounts",
        "tabToolCountParity",
        "callbackTools",
        "callbackToolCount",
        "callbackToolParity",
        "alwaysVisibleTools",
        "alwaysVisibleToolCount",
        "alwaysVisibleToolParity",
        "executionCounts",
        "executionCountParity",
        "resultModeCounts",
        "resultModeCountParity",
        "shellSafetyPolicy",
    ):
        aggregate_key = "toolRegistry" + key[:1].upper() + key[1:]
        if tools_parsers_group.get(aggregate_key) != tool_coverage.get(key):
            raise AssertionError(f"coverage index tools/parsers registry detail {aggregate_key} mismatch: {tools_parsers_group}")
    shell_policy = tools_parsers_group.get("toolRegistryShellSafetyPolicy") or {}
    if shell_policy.get("availability") != "alwaysVisible" or shell_policy.get("dangerSampleBlocked") is not True:
        raise AssertionError(f"coverage index shell safety policy mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("alwaysVisibleToolCount") != tool_coverage.get("alwaysVisibleCount"):
        raise AssertionError(f"coverage index tools/parsers always-visible tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("boundedCatalogueLimit") != tool_coverage.get("boundedCatalogueLimit"):
        raise AssertionError(f"coverage index tools/parsers bounded catalogue limit mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("familyFanoutCount", 0) < 7:
        raise AssertionError(f"coverage index tools/parsers family fanout count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("familyFanoutTools") != EXPECTED_FAMILY_FANOUT_TOOLS:
        raise AssertionError(f"coverage index tools/parsers family fanout tool map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserStructuredTools") != EXPECTED_RESULT_PARSER_STRUCTURED_TOOLS:
        raise AssertionError(f"coverage index tools/parsers structured parser tool set mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserRawOnlyTools") != EXPECTED_RESULT_PARSER_RAW_ONLY_TOOLS:
        raise AssertionError(f"coverage index tools/parsers raw-only parser tool set mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("stateKeyCount", 0) < 5:
        raise AssertionError(f"coverage index tools/parsers state key count mismatch: {tools_parsers_group}")
    tool_flow = request("GET", "/qa/tool-flow-coverage")
    tool_execution_matrix = request("GET", "/qa/tool-execution-matrix")
    result_parser = request("GET", "/qa/result-parser-coverage")
    parser_tool_matrix = request("GET", "/qa/parser-tool-matrix")
    if tool_execution_matrix.get("ok") is not True:
        raise AssertionError(f"tool execution matrix route failed: {tool_execution_matrix}")
    if tools_parsers_group.get("toolExecutionMatrixCount") != tool_execution_matrix.get("toolCount"):
        raise AssertionError(f"coverage index tools/parsers tool execution count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolExecutionMatrixParity") != tool_execution_matrix.get("rowParity"):
        raise AssertionError(f"coverage index tools/parsers tool execution parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolExecutionMatrixProofFileParity") != tool_execution_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tools/parsers tool execution proof parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolExecutionMatrixAuthorizationPolicyCount") != tool_execution_matrix.get("authorizationPolicyCount"):
        raise AssertionError(f"coverage index tools/parsers tool execution auth policy count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolExecutionMatrixExecutionStateCount") != tool_execution_matrix.get("executionStateCount"):
        raise AssertionError(f"coverage index tools/parsers tool execution state count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolExecutionMatrixSourceHookParity") != tool_execution_matrix.get("sourceHookParity"):
        raise AssertionError(f"coverage index tools/parsers tool execution source hook parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserCounts") != result_parser.get("counts"):
        raise AssertionError(f"coverage index tools/parsers result-parser counts mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserParsedTools") != result_parser.get("parsedTools"):
        raise AssertionError(f"coverage index tools/parsers result-parser parsed tools mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserRawOnlyParsedTools") != result_parser.get("rawOnlyTools"):
        raise AssertionError(f"coverage index tools/parsers result-parser raw-only tools mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserFailures") != result_parser.get("failures"):
        raise AssertionError(f"coverage index tools/parsers result-parser failures mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultParserFailureCount") != len(result_parser.get("failures") or []):
        raise AssertionError(f"coverage index tools/parsers result-parser failure count mismatch: {tools_parsers_group}")
    if parser_tool_matrix.get("ok") is not True:
        raise AssertionError(f"parser tool matrix route failed: {parser_tool_matrix}")
    if tools_parsers_group.get("parserToolMatrixCount") != parser_tool_matrix.get("toolCount"):
        raise AssertionError(f"coverage index tools/parsers parser tool matrix count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("parserToolMatrixParsedParity") != parser_tool_matrix.get("parsedParity"):
        raise AssertionError(f"coverage index tools/parsers parser tool matrix parsed parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("parserToolMatrixToolExecutionParity") != parser_tool_matrix.get("toolExecutionParity"):
        raise AssertionError(f"coverage index tools/parsers parser tool matrix execution parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("parserToolMatrixProofFileParity") != parser_tool_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tools/parsers parser tool matrix proof parity mismatch: {tools_parsers_group}")
    for field in (
        "subdomains",
        "webUrls",
        "vulnSources",
        "vulnTitles",
        "ports",
        "networkHosts",
        "osintPlatforms",
        "postLabels",
        "rawTools",
    ):
        aggregate_field = "resultParser" + field[:1].upper() + field[1:]
        if tools_parsers_group.get(aggregate_field) != result_parser.get(field):
            raise AssertionError(f"coverage index tools/parsers {aggregate_field} mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowProofCount") != tool_flow.get("proofCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowProofs") != tool_flow.get("proofs"):
        raise AssertionError(f"coverage index tools/parsers tool-flow proof list mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowProofFileParity") != tool_flow.get("proofFileParity"):
        raise AssertionError(f"coverage index tools/parsers tool-flow proof-file parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowToolCount") != tool_flow.get("toolCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow tool count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowCallbackCount") != tool_flow.get("callbackCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow callback count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowRoutes") != tool_flow.get("routes"):
        raise AssertionError(f"coverage index tools/parsers tool-flow routes mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowRouteCount") != len(tool_flow.get("routes") or []):
        raise AssertionError(f"coverage index tools/parsers tool-flow route count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowFamilies") != tool_flow.get("families"):
        raise AssertionError(f"coverage index tools/parsers tool-flow families mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowFamilyCount") != len(tool_flow.get("families") or []):
        raise AssertionError(f"coverage index tools/parsers tool-flow family count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowDomains") != tool_flow.get("flowDomains"):
        raise AssertionError(f"coverage index tools/parsers tool-flow domains mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowDomainCount") != tool_flow.get("flowDomainCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow domain count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowDomainParity") != tool_flow.get("flowDomainParity"):
        raise AssertionError(f"coverage index tools/parsers tool-flow domain parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowDomainProofFileParity") != tool_flow.get("flowDomainProofFileParity"):
        raise AssertionError(f"coverage index tools/parsers tool-flow domain proof parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowStateKeys") != tool_flow.get("stateKeys"):
        raise AssertionError(f"coverage index tools/parsers tool-flow state keys mismatch: {tools_parsers_group}")
    if tool_flow.get("stateKeyParity") is not True:
        raise AssertionError(f"tool-flow state key parity mismatch: {tool_flow}")
    if tools_parsers_group.get("toolFlowStateKeyCount") != tool_flow.get("stateKeyCount"):
        raise AssertionError(f"coverage index tools/parsers tool-flow state key count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowStateKeyParity") != tool_flow.get("stateKeyParity"):
        raise AssertionError(f"coverage index tools/parsers tool-flow state key parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowContracts") != tool_flow.get("contracts"):
        raise AssertionError(f"coverage index tools/parsers tool-flow contracts mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolFlowContractCount") != len(tool_flow.get("contracts") or {}):
        raise AssertionError(f"coverage index tools/parsers tool-flow contract count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolSchemaCap") != tool_flow.get("toolSchemaCap"):
        raise AssertionError(f"coverage index tools/parsers schema cap mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolSchemaPolicy") != tool_flow.get("toolSchemaPolicy"):
        raise AssertionError(f"coverage index tools/parsers schema policy mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolCatalogRoute") != tool_flow.get("toolCatalogRoute"):
        raise AssertionError(f"coverage index tools/parsers catalog route mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("structuredResultModeCount") != tool_flow.get("structuredResultModeCount"):
        raise AssertionError(f"coverage index tools/parsers structured result mode count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("rawResultModeCount") != tool_flow.get("rawResultModeCount"):
        raise AssertionError(f"coverage index tools/parsers raw result mode count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("resultModeCountParity") != tool_flow.get("resultModeCountParity"):
        raise AssertionError(f"coverage index tools/parsers result mode parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatuses") != tool_flow.get("tabActivityStatuses"):
        raise AssertionError(f"coverage index tools/parsers tab activity statuses mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusCount") != tool_flow.get("tabActivityStatusCount"):
        raise AssertionError(f"coverage index tools/parsers tab activity status count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusParity") != tool_flow.get("tabActivityStatusParity"):
        raise AssertionError(f"coverage index tools/parsers tab activity status parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityIndicatorContract") != tool_flow.get("tabActivityIndicatorContract"):
        raise AssertionError(f"coverage index tools/parsers tab activity indicator contract mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofs") != tool_flow.get("tabActivityStatusProofs"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofCount") != tool_flow.get("tabActivityStatusProofCount"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofParity") != tool_flow.get("tabActivityStatusProofParity"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("tabActivityStatusProofFileParity") != tool_flow.get("tabActivityStatusProofFileParity"):
        raise AssertionError(f"coverage index tools/parsers tab activity status proof-file parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaces") != tool_flow.get("toolVisualSurfaces"):
        raise AssertionError(f"coverage index tools/parsers visual surfaces mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceCount") != tool_flow.get("toolVisualSurfaceCount"):
        raise AssertionError(f"coverage index tools/parsers visual surface count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceParity") != tool_flow.get("toolVisualSurfaceParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofs") != tool_flow.get("toolVisualSurfaceProofs"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof map mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofCount") != tool_flow.get("toolVisualSurfaceProofCount"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof count mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofParity") != tool_flow.get("toolVisualSurfaceProofParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof parity mismatch: {tools_parsers_group}")
    if tools_parsers_group.get("toolVisualSurfaceProofFileParity") != tool_flow.get("toolVisualSurfaceProofFileParity"):
        raise AssertionError(f"coverage index tools/parsers visual surface proof-file parity mismatch: {tools_parsers_group}")
    tabs_sessions_group = groups.get("tabsAndSessions") or {}
    tab_tool_function_flow = request("GET", "/qa/tab-tool-function-flow")
    if tabs_sessions_group.get("interactionModeCount", 0) < 3:
        raise AssertionError(f"coverage index tabs/sessions mode count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("coveredTabCount", 0) < 9:
        raise AssertionError(f"coverage index tabs/sessions tab count mismatch: {tabs_sessions_group}")
    if tab_tool_function_flow.get("ok") is not True:
        raise AssertionError(f"tab-tool-function flow route failed: {tab_tool_function_flow}")
    if tabs_sessions_group.get("tabToolFunctionFlowCount") != tab_tool_function_flow.get("tabCount"):
        raise AssertionError(f"coverage index tabs/sessions tab-tool-function count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabToolFunctionFlowParity") != tab_tool_function_flow.get("tabParity"):
        raise AssertionError(f"coverage index tabs/sessions tab-tool-function parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabToolFunctionFlowProofFileParity") != tab_tool_function_flow.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab-tool-function proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabToolFunctionFlowFunctionCount") != tab_tool_function_flow.get("functionFlowCount"):
        raise AssertionError(f"coverage index tabs/sessions tab-tool-function function count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabToolFunctionFlowAgentLoopPhaseCount") != tab_tool_function_flow.get("agentLoopPhaseCount"):
        raise AssertionError(f"coverage index tabs/sessions tab-tool-function agent loop count mismatch: {tabs_sessions_group}")
    tab_proof_family_matrix = request("GET", "/qa/tab-proof-family-matrix")
    if tab_proof_family_matrix.get("ok") is not True:
        raise AssertionError(f"tab proof family matrix route failed: {tab_proof_family_matrix}")
    if tabs_sessions_group.get("tabProofFamilyMatrixCount") != tab_proof_family_matrix.get("familyCount"):
        raise AssertionError(f"coverage index tabs/sessions tab proof family count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabProofFamilyMatrixProofFileParity") != tab_proof_family_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab proof family proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabProofFamilyMatrixFamilyProofFileParity") != tab_proof_family_matrix.get("familyProofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab proof family file parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabProofFamilyMatrixProofLedgerFamilyCount") != tab_proof_family_matrix.get("proofLedgerTabProofFamilyCount"):
        raise AssertionError(f"coverage index tabs/sessions tab proof family ledger count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stateKeyCount", 0) < 12:
        raise AssertionError(f"coverage index tabs/sessions state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("actionStateKeyCount", 0) < 26:
        raise AssertionError(f"coverage index tabs/sessions action state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabTabs") != subtab_coverage.get("tabs"):
        raise AssertionError(f"coverage index tabs/sessions subtab tab map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabProofCount") != subtab_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions subtab proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabProofFileParity") != subtab_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions subtab proof-file parity mismatch: {tabs_sessions_group}")
    if subtab_lifecycle_matrix.get("ok") is not True:
        raise AssertionError(f"subtab lifecycle matrix route failed: {subtab_lifecycle_matrix}")
    if tabs_sessions_group.get("subtabLifecycleMatrixCount") != subtab_lifecycle_matrix.get("subtabCount"):
        raise AssertionError(f"coverage index tabs/sessions subtab lifecycle count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabLifecycleMatrixProofOwnerFileParity") != subtab_lifecycle_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index tabs/sessions subtab lifecycle owner parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabLifecycleMatrixProofFileParity") != subtab_lifecycle_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions subtab lifecycle proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("subtabLifecycleMatrixTabToolFunctionFlowCount") != subtab_lifecycle_matrix.get("tabToolFunctionFlowCount"):
        raise AssertionError(f"coverage index tabs/sessions subtab lifecycle tab-flow count mismatch: {tabs_sessions_group}")
    agent_loop = request("GET", "/qa/agent-loop-coverage")
    agent_loop_phase_matrix = request("GET", "/qa/agent-loop-phase-matrix")
    agent_tool_auth = request("GET", "/qa/agent-tool-authorization-coverage")
    if tabs_sessions_group.get("agentLoopStateKeyCount") != agent_loop.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop state key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopStateKeys") != agent_loop.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions agent loop state key list mismatch: {tabs_sessions_group}")
    if agent_loop.get("stateKeyParity") is not True:
        raise AssertionError(f"agent loop state-key parity mismatch: {agent_loop}")
    if tabs_sessions_group.get("agentLoopStateKeyParity") != agent_loop.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopCurrentMode") != agent_loop.get("currentMode"):
        raise AssertionError(f"coverage index tabs/sessions agent loop current mode mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopMaxIterations") != agent_loop.get("maxIterations"):
        raise AssertionError(f"coverage index tabs/sessions agent loop max iterations mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopProofCount") != agent_loop.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopProofs") != agent_loop.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions agent loop proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopProofFileParity") != agent_loop.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop proof file parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopVisualStateKeys") != agent_loop.get("visualStateKeys"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopVisualStateKeyCount") != agent_loop.get("visualStateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state key count mismatch: {tabs_sessions_group}")
    if agent_loop.get("visualStateKeyParity") is not True:
        raise AssertionError(f"agent loop visual state key parity mismatch: {agent_loop}")
    if tabs_sessions_group.get("agentLoopVisualStateKeyParity") != agent_loop.get("visualStateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop visual state key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhases") != agent_loop.get("loopPhases"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phases mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseCount") != agent_loop.get("loopPhaseCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseParity") != agent_loop.get("loopPhaseParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofs") != agent_loop.get("loopPhaseProofs"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofCount") != agent_loop.get("loopPhaseProofCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofParity") != agent_loop.get("loopPhaseProofParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseProofFileParity") != agent_loop.get("loopPhaseProofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase proof-file parity mismatch: {tabs_sessions_group}")
    if agent_loop_phase_matrix.get("ok") is not True:
        raise AssertionError(f"agent loop phase matrix route failed: {agent_loop_phase_matrix}")
    if tabs_sessions_group.get("agentLoopPhaseMatrixCount") != agent_loop_phase_matrix.get("phaseCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase matrix count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseMatrixParity") != agent_loop_phase_matrix.get("phaseParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase matrix parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseMatrixSourceCoverageParity") != agent_loop_phase_matrix.get("sourceCoverageParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase matrix source parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopPhaseMatrixProofFileParity") != agent_loop_phase_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop phase matrix proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopModes") != agent_loop.get("modes"):
        raise AssertionError(f"coverage index tabs/sessions agent loop modes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopModeCount") != agent_loop.get("modeCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop mode count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopAgents") != agent_loop.get("agents"):
        raise AssertionError(f"coverage index tabs/sessions agent loop agent contract mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopAgentContractCount") != agent_loop.get("agentContractCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop agent contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopRoutes") != agent_loop.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions agent loop routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopRouteCount") != agent_loop.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop route count mismatch: {tabs_sessions_group}")
    if agent_loop.get("routeParity") is not True:
        raise AssertionError(f"agent loop route parity mismatch: {agent_loop}")
    if tabs_sessions_group.get("agentLoopRouteParity") != agent_loop.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopContracts") != agent_loop.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions agent loop contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopContractCount") != agent_loop.get("contractCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop contract count mismatch: {tabs_sessions_group}")
    if agent_loop.get("contractParity") is not True:
        raise AssertionError(f"agent loop contract parity mismatch: {agent_loop}")
    if tabs_sessions_group.get("agentLoopContractParity") != agent_loop.get("contractParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop contract parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopActionTelemetryFields") != agent_loop.get("actionTelemetryFields"):
        raise AssertionError(f"coverage index tabs/sessions agent loop telemetry fields mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentLoopActionTelemetryFieldCount") != agent_loop.get("actionTelemetryFieldCount"):
        raise AssertionError(f"coverage index tabs/sessions agent loop telemetry count mismatch: {tabs_sessions_group}")
    if agent_loop.get("actionTelemetryFieldParity") is not True:
        raise AssertionError(f"agent loop telemetry field parity mismatch: {agent_loop}")
    if tabs_sessions_group.get("agentLoopActionTelemetryFieldParity") != agent_loop.get("actionTelemetryFieldParity"):
        raise AssertionError(f"coverage index tabs/sessions agent loop telemetry parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationPolicies") != agent_tool_auth.get("policies"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization policies mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationPolicyCount") != agent_tool_auth.get("policyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization policy count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("policyParity") is not True:
        raise AssertionError(f"agent tool authorization policy parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationPolicyParity") != agent_tool_auth.get("policyParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization policy parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationRoutes") != agent_tool_auth.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationRouteCount") != agent_tool_auth.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization route count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("routeParity") is not True:
        raise AssertionError(f"agent tool authorization route parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationRouteParity") != agent_tool_auth.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationStateKeys") != agent_tool_auth.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationStateKeyCount") != agent_tool_auth.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization state-key count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("stateKeyParity") is not True:
        raise AssertionError(f"agent tool authorization state-key parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationStateKeyParity") != agent_tool_auth.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationVisualSurfaces") != agent_tool_auth.get("visualSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization visual surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationVisualSurfaceCount") != agent_tool_auth.get("visualSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization visual surface count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("visualSurfaceParity") is not True:
        raise AssertionError(f"agent tool authorization visual surface parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationVisualSurfaceParity") != agent_tool_auth.get("visualSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization visual surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationTransitions") != agent_tool_auth.get("transitions"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization transitions mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationTransitionCount") != agent_tool_auth.get("transitionCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization transition count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("transitionParity") is not True:
        raise AssertionError(f"agent tool authorization transition parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationTransitionParity") != agent_tool_auth.get("transitionParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization transition parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationPendingApproval") != agent_tool_auth.get("pendingApproval"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization pending approval mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationProofs") != agent_tool_auth.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("agentToolAuthorizationProofCount") != agent_tool_auth.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization proof count mismatch: {tabs_sessions_group}")
    if agent_tool_auth.get("proofFileParity") is not True:
        raise AssertionError(f"agent tool authorization proof-file parity mismatch: {agent_tool_auth}")
    if tabs_sessions_group.get("agentToolAuthorizationProofFileParity") != agent_tool_auth.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions agent tool authorization proof-file parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatuses") != tool_flow.get("tabActivityStatuses"):
        raise AssertionError(f"coverage index tabs/sessions tab activity statuses mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusCount") != tool_flow.get("tabActivityStatusCount"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusParity") != tool_flow.get("tabActivityStatusParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityIndicatorContract") != tool_flow.get("tabActivityIndicatorContract"):
        raise AssertionError(f"coverage index tabs/sessions tab activity indicator contract mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofs") != tool_flow.get("tabActivityStatusProofs"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofCount") != tool_flow.get("tabActivityStatusProofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofParity") != tool_flow.get("tabActivityStatusProofParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActivityStatusProofFileParity") != tool_flow.get("tabActivityStatusProofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab activity status proof-file parity mismatch: {tabs_sessions_group}")
    session_coverage = request("GET", "/qa/session-coverage")
    if tabs_sessions_group.get("sessionRoutes") != session_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions session route list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionRouteCount") != len(session_coverage.get("routes") or []):
        raise AssertionError(f"coverage index tabs/sessions session route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionContracts") != session_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions session contract map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionContractCount") != len(session_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions session contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionProofs") != session_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions session proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionProofCount") != session_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions session proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionProofFileParity") != session_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions session proof-file parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionStateKeys") != session_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions session state-key list mismatch: {tabs_sessions_group}")
    if session_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"session coverage state-key parity mismatch: {session_coverage}")
    if tabs_sessions_group.get("sessionStateKeyCount") != session_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions session state-key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionStateKeyParity") != session_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions session state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaces") != session_coverage.get("sessionWorkflowSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions workflow surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceCount") != session_coverage.get("sessionWorkflowSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceParity") != session_coverage.get("sessionWorkflowSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofs") != session_coverage.get("sessionWorkflowSurfaceProofs"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofCount") != session_coverage.get("sessionWorkflowSurfaceProofCount"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofParity") != session_coverage.get("sessionWorkflowSurfaceProofParity"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowSurfaceProofFileParity") != session_coverage.get("sessionWorkflowSurfaceProofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions workflow surface proof-file parity mismatch: {tabs_sessions_group}")
    tab_action_coverage = request("GET", "/qa/tab-action-coverage")
    session_workflow_matrix = request("GET", "/qa/session-workflow-matrix")
    if session_workflow_matrix.get("ok") is not True:
        raise AssertionError(f"session workflow matrix route failed: {session_workflow_matrix}")
    if session_workflow_matrix.get("workflowCount") != session_coverage.get("sessionWorkflowSurfaceCount"):
        raise AssertionError(f"session workflow matrix workflow count mismatch: {session_workflow_matrix}")
    if session_workflow_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"session workflow matrix owner parity mismatch: {session_workflow_matrix}")
    if session_workflow_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"session workflow matrix proof-file parity mismatch: {session_workflow_matrix}")
    if session_workflow_matrix.get("tabActionRouteCount") != len(tab_action_coverage.get("routes") or []):
        raise AssertionError(f"session workflow matrix tab-action route count mismatch: {session_workflow_matrix}")
    if tabs_sessions_group.get("sessionWorkflowMatrixCount") != session_workflow_matrix.get("workflowCount"):
        raise AssertionError(f"coverage index session workflow matrix count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowMatrixProofOwnerFileParity") != session_workflow_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index session workflow matrix owner parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowMatrixProofFileParity") != session_workflow_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index session workflow matrix proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("sessionWorkflowMatrixTabActionRouteCount") != session_workflow_matrix.get("tabActionRouteCount"):
        raise AssertionError(f"coverage index session workflow matrix tab-action route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionTabs") != tab_action_coverage.get("tabs"):
        raise AssertionError(f"coverage index tabs/sessions tab action tabs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionRoutes") != tab_action_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions tab action route list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionRouteCount") != len(tab_action_coverage.get("routes") or []):
        raise AssertionError(f"coverage index tabs/sessions tab action route count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionContracts") != tab_action_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions tab action contract map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionContractCount") != len(tab_action_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions tab action contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionProofs") != tab_action_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions tab action proof list mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionProofCount") != tab_action_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionProofFileParity") != tab_action_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action proof-file parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionStateKeys") != tab_action_coverage.get("actionStateKeys"):
        raise AssertionError(f"coverage index tabs/sessions tab action state-key list mismatch: {tabs_sessions_group}")
    if tab_action_coverage.get("actionStateKeyParity") is not True:
        raise AssertionError(f"tab action coverage state-key parity mismatch: {tab_action_coverage}")
    if tabs_sessions_group.get("tabActionStateKeyCount") != tab_action_coverage.get("actionStateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action state-key count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionStateKeyParity") != tab_action_coverage.get("actionStateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaces") != tab_action_coverage.get("tabActionSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions tab action surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceCount") != tab_action_coverage.get("tabActionSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceParity") != tab_action_coverage.get("tabActionSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofs") != tab_action_coverage.get("tabActionSurfaceProofs"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof map mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofCount") != tab_action_coverage.get("tabActionSurfaceProofCount"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofParity") != tab_action_coverage.get("tabActionSurfaceProofParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceProofFileParity") != tab_action_coverage.get("tabActionSurfaceProofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions tab action surface proof-file parity mismatch: {tabs_sessions_group}")
    action_state_inventory = request("GET", "/qa/action-state-inventory")
    tab_action_surface_matrix = request("GET", "/qa/tab-action-surface-matrix")
    if tab_action_surface_matrix.get("ok") is not True:
        raise AssertionError(f"tab action surface matrix route failed: {tab_action_surface_matrix}")
    if tab_action_surface_matrix.get("surfaceCount") != tab_action_coverage.get("tabActionSurfaceCount"):
        raise AssertionError(f"tab action surface matrix surface count mismatch: {tab_action_surface_matrix}")
    if tab_action_surface_matrix.get("proofOwnerFileParity") is not True:
        raise AssertionError(f"tab action surface matrix owner parity mismatch: {tab_action_surface_matrix}")
    if tab_action_surface_matrix.get("proofFileParity") is not True:
        raise AssertionError(f"tab action surface matrix proof-file parity mismatch: {tab_action_surface_matrix}")
    if tab_action_surface_matrix.get("actionStateCount") != action_state_inventory.get("actionStateCount"):
        raise AssertionError(f"tab action surface matrix action-state count mismatch: {tab_action_surface_matrix}")
    if tabs_sessions_group.get("tabActionSurfaceMatrixCount") != tab_action_surface_matrix.get("surfaceCount"):
        raise AssertionError(f"coverage index tab action surface matrix count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceMatrixProofOwnerFileParity") != tab_action_surface_matrix.get("proofOwnerFileParity"):
        raise AssertionError(f"coverage index tab action surface matrix owner parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceMatrixProofFileParity") != tab_action_surface_matrix.get("proofFileParity"):
        raise AssertionError(f"coverage index tab action surface matrix proof parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("tabActionSurfaceMatrixActionStateCount") != tab_action_surface_matrix.get("actionStateCount"):
        raise AssertionError(f"coverage index tab action surface matrix action-state count mismatch: {tabs_sessions_group}")
    recon_coverage = request("GET", "/qa/recon-coverage")
    if tabs_sessions_group.get("reconSurfaces") != recon_coverage.get("reconSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions recon surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconSurfaceCount") != recon_coverage.get("reconSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions recon surface count mismatch: {tabs_sessions_group}")
    if recon_coverage.get("reconSurfaceParity") is not True:
        raise AssertionError(f"recon coverage surface parity mismatch: {recon_coverage}")
    if tabs_sessions_group.get("reconSurfaceParity") != recon_coverage.get("reconSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions recon surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconRoutes") != recon_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions recon routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconRouteCount") != recon_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions recon route count mismatch: {tabs_sessions_group}")
    if recon_coverage.get("routeParity") is not True:
        raise AssertionError(f"recon coverage route parity mismatch: {recon_coverage}")
    if tabs_sessions_group.get("reconRouteParity") != recon_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions recon route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconStateKeys") != recon_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions recon state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconStateKeyCount") != recon_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions recon state-key count mismatch: {tabs_sessions_group}")
    if recon_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"recon coverage state-key parity mismatch: {recon_coverage}")
    if tabs_sessions_group.get("reconStateKeyParity") != recon_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions recon state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconContracts") != recon_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions recon contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconContractCount") != len(recon_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions recon contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconProofs") != recon_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions recon proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reconProofCount") != recon_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions recon proof count mismatch: {tabs_sessions_group}")
    if recon_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"recon coverage proof-file parity mismatch: {recon_coverage}")
    if tabs_sessions_group.get("reconProofFileParity") != recon_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions recon proof-file parity mismatch: {tabs_sessions_group}")
    web_coverage = request("GET", "/qa/web-coverage")
    if tabs_sessions_group.get("webSurfaces") != web_coverage.get("webSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions web surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webSurfaceCount") != web_coverage.get("webSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions web surface count mismatch: {tabs_sessions_group}")
    if web_coverage.get("webSurfaceParity") is not True:
        raise AssertionError(f"web coverage surface parity mismatch: {web_coverage}")
    if tabs_sessions_group.get("webSurfaceParity") != web_coverage.get("webSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions web surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webRoutes") != web_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions web routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webRouteCount") != web_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions web route count mismatch: {tabs_sessions_group}")
    if web_coverage.get("routeParity") is not True:
        raise AssertionError(f"web coverage route parity mismatch: {web_coverage}")
    if tabs_sessions_group.get("webRouteParity") != web_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions web route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webStateKeys") != web_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions web state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webStateKeyCount") != web_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions web state-key count mismatch: {tabs_sessions_group}")
    if web_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"web coverage state-key parity mismatch: {web_coverage}")
    if tabs_sessions_group.get("webStateKeyParity") != web_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions web state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webContracts") != web_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions web contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webContractCount") != len(web_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions web contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webProofs") != web_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions web proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("webProofCount") != web_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions web proof count mismatch: {tabs_sessions_group}")
    if web_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"web coverage proof-file parity mismatch: {web_coverage}")
    if tabs_sessions_group.get("webProofFileParity") != web_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions web proof-file parity mismatch: {tabs_sessions_group}")
    network_coverage = request("GET", "/qa/network-coverage")
    if tabs_sessions_group.get("networkSurfaces") != network_coverage.get("networkSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions network surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkSurfaceCount") != network_coverage.get("networkSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions network surface count mismatch: {tabs_sessions_group}")
    if network_coverage.get("networkSurfaceParity") is not True:
        raise AssertionError(f"network coverage surface parity mismatch: {network_coverage}")
    if tabs_sessions_group.get("networkSurfaceParity") != network_coverage.get("networkSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions network surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkRoutes") != network_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions network routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkRouteCount") != network_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions network route count mismatch: {tabs_sessions_group}")
    if network_coverage.get("routeParity") is not True:
        raise AssertionError(f"network coverage route parity mismatch: {network_coverage}")
    if tabs_sessions_group.get("networkRouteParity") != network_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions network route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkStateKeys") != network_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions network state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkStateKeyCount") != network_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions network state-key count mismatch: {tabs_sessions_group}")
    if network_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"network coverage state-key parity mismatch: {network_coverage}")
    if tabs_sessions_group.get("networkStateKeyParity") != network_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions network state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkContracts") != network_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions network contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkContractCount") != len(network_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions network contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkProofs") != network_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions network proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("networkProofCount") != network_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions network proof count mismatch: {tabs_sessions_group}")
    if network_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"network coverage proof-file parity mismatch: {network_coverage}")
    if tabs_sessions_group.get("networkProofFileParity") != network_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions network proof-file parity mismatch: {tabs_sessions_group}")
    creds_coverage = request("GET", "/qa/creds-coverage")
    if tabs_sessions_group.get("credsSurfaces") != creds_coverage.get("credsSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions creds surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsSurfaceCount") != creds_coverage.get("credsSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions creds surface count mismatch: {tabs_sessions_group}")
    if creds_coverage.get("credsSurfaceParity") is not True:
        raise AssertionError(f"creds coverage surface parity mismatch: {creds_coverage}")
    if tabs_sessions_group.get("credsSurfaceParity") != creds_coverage.get("credsSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions creds surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsRoutes") != creds_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions creds routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsRouteCount") != creds_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions creds route count mismatch: {tabs_sessions_group}")
    if creds_coverage.get("routeParity") is not True:
        raise AssertionError(f"creds coverage route parity mismatch: {creds_coverage}")
    if tabs_sessions_group.get("credsRouteParity") != creds_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions creds route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsStateKeys") != creds_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions creds state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsStateKeyCount") != creds_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions creds state-key count mismatch: {tabs_sessions_group}")
    if creds_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"creds coverage state-key parity mismatch: {creds_coverage}")
    if tabs_sessions_group.get("credsStateKeyParity") != creds_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions creds state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsContracts") != creds_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions creds contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsContractCount") != len(creds_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions creds contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsProofs") != creds_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions creds proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("credsProofCount") != creds_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions creds proof count mismatch: {tabs_sessions_group}")
    if creds_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"creds coverage proof-file parity mismatch: {creds_coverage}")
    if tabs_sessions_group.get("credsProofFileParity") != creds_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions creds proof-file parity mismatch: {tabs_sessions_group}")
    exploit_coverage = request("GET", "/qa/exploit-coverage")
    if tabs_sessions_group.get("exploitSurfaces") != exploit_coverage.get("exploitSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions exploit surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitSurfaceCount") != exploit_coverage.get("exploitSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions exploit surface count mismatch: {tabs_sessions_group}")
    if exploit_coverage.get("exploitSurfaceParity") is not True:
        raise AssertionError(f"exploit coverage surface parity mismatch: {exploit_coverage}")
    if tabs_sessions_group.get("exploitSurfaceParity") != exploit_coverage.get("exploitSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions exploit surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitRoutes") != exploit_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions exploit routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitRouteCount") != exploit_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions exploit route count mismatch: {tabs_sessions_group}")
    if exploit_coverage.get("routeParity") is not True:
        raise AssertionError(f"exploit coverage route parity mismatch: {exploit_coverage}")
    if tabs_sessions_group.get("exploitRouteParity") != exploit_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions exploit route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitStateKeys") != exploit_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions exploit state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitStateKeyCount") != exploit_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions exploit state-key count mismatch: {tabs_sessions_group}")
    if exploit_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"exploit coverage state-key parity mismatch: {exploit_coverage}")
    if tabs_sessions_group.get("exploitStateKeyParity") != exploit_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions exploit state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitContracts") != exploit_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions exploit contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitContractCount") != len(exploit_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions exploit contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitProofs") != exploit_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions exploit proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("exploitProofCount") != exploit_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions exploit proof count mismatch: {tabs_sessions_group}")
    if exploit_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"exploit coverage proof-file parity mismatch: {exploit_coverage}")
    if tabs_sessions_group.get("exploitProofFileParity") != exploit_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions exploit proof-file parity mismatch: {tabs_sessions_group}")
    post_coverage = request("GET", "/qa/post-coverage")
    if tabs_sessions_group.get("postSurfaces") != post_coverage.get("postSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions post surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postSurfaceCount") != post_coverage.get("postSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions post surface count mismatch: {tabs_sessions_group}")
    if post_coverage.get("postSurfaceParity") is not True:
        raise AssertionError(f"post coverage surface parity mismatch: {post_coverage}")
    if tabs_sessions_group.get("postSurfaceParity") != post_coverage.get("postSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions post surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postRoutes") != post_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions post routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postRouteCount") != post_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions post route count mismatch: {tabs_sessions_group}")
    if post_coverage.get("routeParity") is not True:
        raise AssertionError(f"post coverage route parity mismatch: {post_coverage}")
    if tabs_sessions_group.get("postRouteParity") != post_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions post route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postStateKeys") != post_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions post state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postStateKeyCount") != post_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions post state-key count mismatch: {tabs_sessions_group}")
    if post_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"post coverage state-key parity mismatch: {post_coverage}")
    if tabs_sessions_group.get("postStateKeyParity") != post_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions post state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postContracts") != post_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions post contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postContractCount") != len(post_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions post contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postProofs") != post_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions post proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("postProofCount") != post_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions post proof count mismatch: {tabs_sessions_group}")
    if post_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"post coverage proof-file parity mismatch: {post_coverage}")
    if tabs_sessions_group.get("postProofFileParity") != post_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions post proof-file parity mismatch: {tabs_sessions_group}")
    osint_coverage = request("GET", "/qa/osint-coverage")
    if tabs_sessions_group.get("osintSurfaces") != osint_coverage.get("osintSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions osint surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintSurfaceCount") != osint_coverage.get("osintSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions osint surface count mismatch: {tabs_sessions_group}")
    if osint_coverage.get("osintSurfaceParity") is not True:
        raise AssertionError(f"osint coverage surface parity mismatch: {osint_coverage}")
    if tabs_sessions_group.get("osintSurfaceParity") != osint_coverage.get("osintSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions osint surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintRoutes") != osint_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions osint routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintRouteCount") != osint_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions osint route count mismatch: {tabs_sessions_group}")
    if osint_coverage.get("routeParity") is not True:
        raise AssertionError(f"osint coverage route parity mismatch: {osint_coverage}")
    if tabs_sessions_group.get("osintRouteParity") != osint_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions osint route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintStateKeys") != osint_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions osint state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintStateKeyCount") != osint_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions osint state-key count mismatch: {tabs_sessions_group}")
    if osint_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"osint coverage state-key parity mismatch: {osint_coverage}")
    if tabs_sessions_group.get("osintStateKeyParity") != osint_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions osint state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintContracts") != osint_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions osint contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintContractCount") != len(osint_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions osint contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintProofs") != osint_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions osint proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("osintProofCount") != osint_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions osint proof count mismatch: {tabs_sessions_group}")
    if osint_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"osint coverage proof-file parity mismatch: {osint_coverage}")
    if tabs_sessions_group.get("osintProofFileParity") != osint_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions osint proof-file parity mismatch: {tabs_sessions_group}")
    report_coverage = request("GET", "/qa/report-coverage")
    if tabs_sessions_group.get("reportSurfaces") != report_coverage.get("reportSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions report surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportSurfaceCount") != report_coverage.get("reportSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions report surface count mismatch: {tabs_sessions_group}")
    if report_coverage.get("reportSurfaceParity") is not True:
        raise AssertionError(f"report coverage surface parity mismatch: {report_coverage}")
    if tabs_sessions_group.get("reportSurfaceParity") != report_coverage.get("reportSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions report surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportRoutes") != report_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions report routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportRouteCount") != report_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions report route count mismatch: {tabs_sessions_group}")
    if report_coverage.get("routeParity") is not True:
        raise AssertionError(f"report coverage route parity mismatch: {report_coverage}")
    if tabs_sessions_group.get("reportRouteParity") != report_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions report route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportStateKeys") != report_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions report state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportStateKeyCount") != report_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions report state-key count mismatch: {tabs_sessions_group}")
    if report_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"report coverage state-key parity mismatch: {report_coverage}")
    if tabs_sessions_group.get("reportStateKeyParity") != report_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions report state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportContracts") != report_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions report contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportContractCount") != len(report_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions report contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportProofs") != report_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions report proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("reportProofCount") != report_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions report proof count mismatch: {tabs_sessions_group}")
    if report_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"report coverage proof-file parity mismatch: {report_coverage}")
    if tabs_sessions_group.get("reportProofFileParity") != report_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions report proof-file parity mismatch: {tabs_sessions_group}")
    stash_coverage = request("GET", "/qa/stash-coverage")
    if tabs_sessions_group.get("stashSurfaces") != stash_coverage.get("stashSurfaces"):
        raise AssertionError(f"coverage index tabs/sessions stash surfaces mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashSurfaceCount") != stash_coverage.get("stashSurfaceCount"):
        raise AssertionError(f"coverage index tabs/sessions stash surface count mismatch: {tabs_sessions_group}")
    if stash_coverage.get("stashSurfaceParity") is not True:
        raise AssertionError(f"stash coverage surface parity mismatch: {stash_coverage}")
    if tabs_sessions_group.get("stashSurfaceParity") != stash_coverage.get("stashSurfaceParity"):
        raise AssertionError(f"coverage index tabs/sessions stash surface parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashRoutes") != stash_coverage.get("routes"):
        raise AssertionError(f"coverage index tabs/sessions stash routes mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashRouteCount") != stash_coverage.get("routeCount"):
        raise AssertionError(f"coverage index tabs/sessions stash route count mismatch: {tabs_sessions_group}")
    if stash_coverage.get("routeParity") is not True:
        raise AssertionError(f"stash coverage route parity mismatch: {stash_coverage}")
    if tabs_sessions_group.get("stashRouteParity") != stash_coverage.get("routeParity"):
        raise AssertionError(f"coverage index tabs/sessions stash route parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashStateKeys") != stash_coverage.get("stateKeys"):
        raise AssertionError(f"coverage index tabs/sessions stash state keys mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashStateKeyCount") != stash_coverage.get("stateKeyCount"):
        raise AssertionError(f"coverage index tabs/sessions stash state-key count mismatch: {tabs_sessions_group}")
    if stash_coverage.get("stateKeyParity") is not True:
        raise AssertionError(f"stash coverage state-key parity mismatch: {stash_coverage}")
    if tabs_sessions_group.get("stashStateKeyParity") != stash_coverage.get("stateKeyParity"):
        raise AssertionError(f"coverage index tabs/sessions stash state-key parity mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashContracts") != stash_coverage.get("contracts"):
        raise AssertionError(f"coverage index tabs/sessions stash contracts mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashContractCount") != len(stash_coverage.get("contracts") or {}):
        raise AssertionError(f"coverage index tabs/sessions stash contract count mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashProofs") != stash_coverage.get("proofs"):
        raise AssertionError(f"coverage index tabs/sessions stash proofs mismatch: {tabs_sessions_group}")
    if tabs_sessions_group.get("stashProofCount") != stash_coverage.get("proofCount"):
        raise AssertionError(f"coverage index tabs/sessions stash proof count mismatch: {tabs_sessions_group}")
    if stash_coverage.get("proofFileParity") is not True:
        raise AssertionError(f"stash coverage proof-file parity mismatch: {stash_coverage}")
    if tabs_sessions_group.get("stashProofFileParity") != stash_coverage.get("proofFileParity"):
        raise AssertionError(f"coverage index tabs/sessions stash proof-file parity mismatch: {tabs_sessions_group}")

    qa = state.get("qaCoverage") or {}
    if "/qa/coverage-index" not in qa.get("stateRoutes", []):
        raise AssertionError(f"/state missing coverage-index route contract: {qa}")


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()
        assert_coverage_index()
        print("coverage-index proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"coverage-index proof failed: {exc}", flush=True)
        raise SystemExit(1)
