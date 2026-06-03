#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"

EXPECTED_ROWS = [
    "cveSemanticEmbeddingState",
    "cveContextPacketSemanticHit",
    "parserToolMatrixFixture",
    "toolEngineContextOpsStatefulCVE",
    "deepRuntimeFlowStatefulCVE",
]

REQUIRED_PROOFS = {
    "state-dependent-contract-matrix-proof.py",
    "cve-import-embedding-coverage-proof.py",
    "tool-engine-context-ops-matrix-proof.py",
    "parser-tool-matrix-proof.py",
    "deep-runtime-flow-coverage-proof.py",
    "result-parser-routing-proof.py",
    "semantic-cve-proof.py",
}


def request(method: str, path: str, body: dict | str | None = None, timeout: float = 45.0):
    if isinstance(body, dict):
        body = json.dumps(body)
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


def seed_state(marker: Path) -> None:
    parsed = request("POST", "/qa/seed-result-parser-fixture")
    if parsed.get("ok") is not True:
        raise AssertionError(f"result parser fixture seed failed: {parsed}")
    seeded = request("POST", "/qa/seed-cve-settings-status")
    if seeded.get("ok") is not True:
        raise AssertionError(f"CVE settings seed failed: {seeded}")
    imported = request("POST", "/qa/cve-settings-action", {
        "action": "importList",
        "source": "CVE-2021-41773\nCVE-2021-42013\nCVE-2022-22965",
        "includeOnly": "CVE-2021-41773,CVE-2022-22965",
    })
    if imported.get("ok") is not True:
        raise AssertionError(f"CVE import-list action failed: {imported}")
    semantic_seed = request("POST", "/qa/seed-semantic-cves")
    if semantic_seed.get("ok") is not True:
        raise AssertionError(f"semantic CVE seed failed: {semantic_seed}")
    packet = request("POST", "/qa/context-packet", {
        "query": "semantic vector lane should find the matching record",
        "maxSnippets": 5,
        "includeAssets": False,
        "includeFindings": False,
        "includeRecentToolOutput": False,
        "includeStash": False,
        "cveMode": "semantic",
    })["packet"]
    if "CVE-QA-SEMANTIC-HIT" not in packet:
        raise AssertionError(f"semantic context packet missing hit:\n{packet}")
    if not marker.exists():
        raise AssertionError("fake CVE embedder was not invoked")


def assert_matrix_shape(matrix: dict) -> dict[str, dict]:
    if matrix.get("route") != "/qa/state-dependent-contract-matrix":
        raise AssertionError(f"state-dependent matrix route label mismatch: {matrix}")
    if matrix.get("proofLevel") != "state-dependent-fixture-and-proof-backed":
        raise AssertionError(f"state-dependent matrix proof level mismatch: {matrix}")
    if matrix.get("rowIds") != EXPECTED_ROWS:
        raise AssertionError(f"state-dependent matrix row order mismatch: {matrix}")
    if matrix.get("rowCount") != len(EXPECTED_ROWS):
        raise AssertionError(f"state-dependent matrix row count mismatch: {matrix}")
    if matrix.get("classificationParity") is not True:
        raise AssertionError(f"state-dependent matrix classification parity mismatch: {matrix}")
    if matrix.get("proofFileParity") is not True:
        raise AssertionError(f"state-dependent matrix proof parity mismatch: {matrix}")
    missing = sorted(REQUIRED_PROOFS.difference(set(matrix.get("proofs") or [])))
    if missing:
        raise AssertionError(f"state-dependent matrix missing proofs {missing}: {matrix}")
    rows = {row.get("id"): row for row in matrix.get("rows") or []}
    for row_id in EXPECTED_ROWS:
        row = rows.get(row_id) or {}
        if row.get("seedRequired") is not True:
            raise AssertionError(f"state-dependent row should require seed {row_id}: {row}")
        if row.get("proofFileParity") is not True:
            raise AssertionError(f"state-dependent row proof parity failed {row_id}: {row}")
        if not row.get("seedCommand"):
            raise AssertionError(f"state-dependent row missing seed command {row_id}: {row}")
    return rows


def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "embedder-called.jsonl"
        embedder = Path(tmp) / "fake-cve-embedder.py"
        embedder.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import json
                import sys
                from pathlib import Path

                Path({str(marker)!r}).write_text(json.dumps({{"argv": sys.argv}}) + "\\n", encoding="utf-8")
                print(json.dumps({{"vector": [1.0, 0.0, 0.0, 0.0], "dimensions": 4}}))
                """
            ),
            encoding="utf-8",
        )
        embedder.chmod(0o755)

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_CVE_EMBEDDER_PATH"] = str(embedder)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

        try:
            if app.wait(timeout=30) != 0:
                raise RuntimeError("build_and_run --verify failed")
            wait_for_app()

            unseeded = request("GET", "/qa/state-dependent-contract-matrix")
            rows = assert_matrix_shape(unseeded)
            if unseeded.get("ok") is not True:
                raise AssertionError(f"unseeded state-dependent matrix should classify gaps without failing: {unseeded}")
            if unseeded.get("seedRequiredRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"unseeded state-dependent seed row count mismatch: {unseeded}")
            if unseeded.get("seededReadyRowCount") != 0:
                raise AssertionError(f"unseeded state-dependent matrix should not be seeded yet: {unseeded}")
            for row in rows.values():
                if row.get("status") != "fixture-required":
                    raise AssertionError(f"unseeded state-dependent row status mismatch: {row}")

            seed_state(marker)
            seeded = request("GET", "/qa/state-dependent-contract-matrix")
            rows = assert_matrix_shape(seeded)
            if seeded.get("ok") is not True:
                raise AssertionError(f"seeded state-dependent matrix failed: {seeded}")
            if seeded.get("seededReadyRowCount") != len(EXPECTED_ROWS):
                raise AssertionError(f"seeded state-dependent ready count mismatch: {seeded}")
            for row in rows.values():
                if row.get("status") != "ready":
                    raise AssertionError(f"seeded state-dependent row not ready: {row}")
                if row.get("contractOK") is not True:
                    raise AssertionError(f"seeded state-dependent row contract failed: {row}")

            state = request("GET", "/state")
            state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
            if "/qa/state-dependent-contract-matrix" not in state_routes:
                raise AssertionError(f"state route list missing state-dependent matrix: {state_routes}")

            index = request("GET", "/qa/coverage-index")
            groups = index.get("groups") or {}
            for group_name in ("chatAndContext", "runtimeAndCache", "toolsAndParsers"):
                group = groups.get(group_name) or {}
                if "/qa/state-dependent-contract-matrix" not in (group.get("endpoints") or []):
                    raise AssertionError(f"coverage index {group_name} missing state-dependent route: {group}")
                if "state-dependent-contract-matrix-proof.py" not in (group.get("proofs") or []):
                    raise AssertionError(f"coverage index {group_name} missing state-dependent proof: {group}")
            chat = groups.get("chatAndContext") or {}
            if chat.get("stateDependentSeedRequiredRows") != seeded.get("rowIds"):
                raise AssertionError(f"coverage index state-dependent row mirror mismatch: {chat}")
            if chat.get("stateDependentSeededReadyRowCount") != seeded.get("seededReadyRowCount"):
                raise AssertionError(f"coverage index state-dependent ready mirror mismatch: {chat}")
            if chat.get("stateDependentClassificationParity") is not True:
                raise AssertionError(f"coverage index state-dependent classification parity mismatch: {chat}")

            print("state-dependent-contract-matrix proof passed")
        finally:
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app.poll() is None:
                app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"state-dependent-contract-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
