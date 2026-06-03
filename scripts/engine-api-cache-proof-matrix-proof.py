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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "ExploitBotEngine"
APP_API = "http://127.0.0.1:9999"

EXPECTED_ROWS = [
    "responsesSessionReuse",
    "toolParserAPIShape",
    "reasoningContentDeltaFields",
    "serverCacheDefaults",
    "turboQuantKVMode",
    "promptL2DiskCache",
    "blockL2DiskCacheHit",
    "hybridSSMReDeriveStatus",
    "streamingParserReuseRoute",
    "runtimeCacheRoute",
]

ENGINE_TESTS = [
    "testsuite/test_responses_session_store.py",
    "testsuite/test_tool_parser_api.py",
    "testsuite/test_server_cache_defaults.py",
    "testsuite/test_kv_quantization_modes.py",
    "testsuite/test_disk_cache_manager.py",
    "testsuite/test_hybrid_ssm_helpers.py",
]

REQUIRED_PROOFS = {
    "engine-api-cache-proof-matrix-proof.py",
    "streaming-parser-reuse-proof.py",
    "runtime-coverage-proof.py",
    "cache-artifact-matrix-proof.py",
    "prove-parser-api.py",
    "prove-block-l2-cache.py",
    "prove-ssm-rederive-status.py",
}


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


def run_engine_tests() -> tuple[str, int]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    python = ENGINE / ".venv" / "bin" / "python"
    cmd = [str(python), "-m", "pytest", "-q", *ENGINE_TESTS]
    result = subprocess.run(
        cmd,
        cwd=ENGINE,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(f"engine pytest failed:\n{result.stdout}")
    match = re.search(r"(\d+)\s+passed", result.stdout)
    passed = int(match.group(1)) if match else 0
    if passed < 20:
        raise AssertionError(f"engine pytest pass count too low ({passed}):\n{result.stdout}")
    return result.stdout, passed


def run() -> None:
    pytest_output, pytest_passed = run_engine_tests()
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        matrix = request("GET", "/qa/engine-api-cache-proof-matrix")
        streaming = request("GET", "/qa/streaming-parser-reuse")
        runtime = request("GET", "/qa/runtime-coverage")
        cache = request("GET", "/qa/cache-artifact-matrix")
        index = request("GET", "/qa/coverage-index")
        state = request("GET", "/state")

        if matrix.get("ok") is not True:
            raise AssertionError(f"engine API/cache proof matrix failed: {matrix}")
        if matrix.get("route") != "/qa/engine-api-cache-proof-matrix":
            raise AssertionError(f"engine API/cache route label mismatch: {matrix}")
        if matrix.get("proofLevel") != "engine-pytest-and-app-route-backed":
            raise AssertionError(f"engine API/cache proof level mismatch: {matrix}")
        if matrix.get("rowIds") != EXPECTED_ROWS:
            raise AssertionError(f"engine API/cache row order mismatch: {matrix}")
        if matrix.get("rowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"engine API/cache row count mismatch: {matrix}")
        if matrix.get("readyRowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"engine API/cache ready row count mismatch: {matrix}")
        if matrix.get("contractParity") is not True:
            raise AssertionError(f"engine API/cache contract parity mismatch: {matrix}")
        if matrix.get("proofFileParity") is not True:
            raise AssertionError(f"engine API/cache proof-file parity mismatch: {matrix}")
        if matrix.get("engineTestFiles") != ENGINE_TESTS:
            raise AssertionError(f"engine API/cache test file list mismatch: {matrix}")
        if matrix.get("enginePytestCommand") != "cd ExploitBotEngine && PYTHONPATH=. .venv/bin/python -m pytest -q " + " ".join(ENGINE_TESTS):
            raise AssertionError(f"engine API/cache pytest command mismatch: {matrix}")
        if matrix.get("enginePytestPassedMinimum", 0) > pytest_passed:
            raise AssertionError(f"engine API/cache route overstates pytest count: {matrix}\n{pytest_output}")

        rows = {row.get("id"): row for row in matrix.get("rows") or []}
        for row_id in EXPECTED_ROWS:
            row = rows.get(row_id) or {}
            if row.get("status") != "ready":
                raise AssertionError(f"engine API/cache row not ready {row_id}: {row}")
            if row.get("contractOK") is not True:
                raise AssertionError(f"engine API/cache row contract failed {row_id}: {row}")
            if row.get("proofFileParity") is not True:
                raise AssertionError(f"engine API/cache row proof parity failed {row_id}: {row}")

        if rows["responsesSessionReuse"].get("testFile") != "testsuite/test_responses_session_store.py":
            raise AssertionError(f"Responses row test file mismatch: {rows['responsesSessionReuse']}")
        if rows["toolParserAPIShape"].get("testFile") != "testsuite/test_tool_parser_api.py":
            raise AssertionError(f"tool parser row test file mismatch: {rows['toolParserAPIShape']}")
        if rows["reasoningContentDeltaFields"].get("streamingContractParity") != streaming.get("contractParity"):
            raise AssertionError(f"reasoning/delta row drifted: {rows['reasoningContentDeltaFields']}")
        if rows["serverCacheDefaults"].get("testFile") != "testsuite/test_server_cache_defaults.py":
            raise AssertionError(f"server cache defaults row test mismatch: {rows['serverCacheDefaults']}")
        if rows["turboQuantKVMode"].get("testFile") != "testsuite/test_kv_quantization_modes.py":
            raise AssertionError(f"TurboQuant row test mismatch: {rows['turboQuantKVMode']}")
        if rows["blockL2DiskCacheHit"].get("cacheArtifactContractParity") != cache.get("contractParity"):
            raise AssertionError(f"block L2 row drifted from cache route: {rows['blockL2DiskCacheHit']}")
        if rows["hybridSSMReDeriveStatus"].get("runtimeSSMArtifactOK") != runtime.get("qwenSSMReDeriveArtifactOK"):
            raise AssertionError(f"hybrid SSM row drifted from runtime route: {rows['hybridSSMReDeriveStatus']}")
        if rows["streamingParserReuseRoute"].get("responsesReuseMode") != streaming.get("responsesStoreSessionMode"):
            raise AssertionError(f"streaming route row drifted: {rows['streamingParserReuseRoute']}")
        if rows["runtimeCacheRoute"].get("cacheComponents") != runtime.get("cacheComponents"):
            raise AssertionError(f"runtime cache route row drifted: {rows['runtimeCacheRoute']}")

        missing_proofs = sorted(REQUIRED_PROOFS.difference(set(matrix.get("proofs") or [])))
        if missing_proofs:
            raise AssertionError(f"engine API/cache matrix missing proofs {missing_proofs}: {matrix}")

        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/engine-api-cache-proof-matrix" not in state_routes:
            raise AssertionError(f"state route list missing engine API/cache matrix: {state_routes}")
        runtime_group = (index.get("groups") or {}).get("runtimeAndCache") or {}
        if "/qa/engine-api-cache-proof-matrix" not in (runtime_group.get("endpoints") or []):
            raise AssertionError(f"coverage index runtime group missing engine API/cache matrix: {runtime_group}")
        if "engine-api-cache-proof-matrix-proof.py" not in (runtime_group.get("proofs") or []):
            raise AssertionError(f"coverage index runtime group missing engine API/cache proof: {runtime_group}")
        if runtime_group.get("engineAPICacheProofRowCount") != len(EXPECTED_ROWS):
            raise AssertionError(f"coverage index runtime group engine API/cache row count mismatch: {runtime_group}")
        if runtime_group.get("engineAPICacheProofContractParity") is not True:
            raise AssertionError(f"coverage index runtime group engine API/cache contract parity mismatch: {runtime_group}")

        print("engine-api-cache-proof-matrix proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"engine-api-cache-proof-matrix proof failed: {exc}", flush=True)
        raise SystemExit(1)
