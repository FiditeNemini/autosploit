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

EXPECTED_REQUIREMENTS = [
    "toolFlowUsage",
    "engineRuntime",
    "localModelLane",
    "contextCarryCompaction",
    "promptInjectionBoundary",
    "cveDatabaseEmbeddings",
    "stashMemoryRetrieval",
    "sessionParallelContinuousBatching",
    "responsesReuseStreamingParser",
    "l2DiskCacheStorageHit",
    "turboQuantKVCache",
    "hybridSSMAsyncReDerive",
    "proofLedgers",
    "releasePackageReadiness",
    "knownGapsTracked",
]

EXPECTED_CONTRACTS = {
    "toolFlowUsage",
    "engineRuntime",
    "localModelLane",
    "contextCarryCompaction",
    "promptInjectionBoundary",
    "cveDatabaseEmbeddings",
    "stashMemoryRetrieval",
    "sessionParallelContinuousBatching",
    "responsesReuseStreamingParser",
    "l2DiskCacheStorageHit",
    "turboQuantKVCache",
    "hybridSSMAsyncReDerive",
    "proofLedgers",
    "releasePackageReadiness",
    "knownGapsTracked",
    "objectiveNotCompleteWhileGapsRemain",
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


def run() -> None:
    env = os.environ.copy()
    env["EXPLOITBOT_TESTING"] = "1"
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)

    try:
        if app.wait(timeout=30) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        payload = request("GET", "/qa/objective-runtime-coverage")
        matrix = request("GET", "/qa/objective-flow-requirement-matrix", timeout=35.0)
        if payload.get("ok") is not True:
            raise AssertionError(f"objective runtime coverage route failed: {payload}")
        if payload.get("route") != "/qa/objective-runtime-coverage":
            raise AssertionError(f"objective runtime coverage route label mismatch: {payload}")
        if payload.get("proofLevel") != "aggregate-route-and-live-artifact-backed":
            raise AssertionError(f"objective runtime coverage proof level mismatch: {payload}")
        if payload.get("objectiveStatus") != "covered-with-known-gaps":
            raise AssertionError(f"objective runtime coverage status mismatch: {payload}")
        if payload.get("objectiveComplete") is not False:
            raise AssertionError(f"objective runtime coverage should not claim completion while gaps remain: {payload}")
        if payload.get("requirements") != EXPECTED_REQUIREMENTS:
            raise AssertionError(f"objective runtime requirement order mismatch: {payload}")
        if payload.get("requirementCount") != len(EXPECTED_REQUIREMENTS):
            raise AssertionError(f"objective runtime requirement count mismatch: {payload}")
        blocked_ids = payload.get("blockedRequirementIds") or []
        if payload.get("blockedRequirementCount") != len(blocked_ids):
            raise AssertionError(f"objective runtime blocked requirement count mismatch: {payload}")
        evidence = payload.get("evidence") or {}
        ready_count = sum(1 for row in evidence.values() if row.get("status") == "ready")
        if payload.get("readyRequirementCount") != ready_count:
            raise AssertionError(f"objective runtime ready requirement count mismatch: {payload}")
        unexpected_blocked = sorted(set(blocked_ids).difference({"releasePackageReadiness"}))
        if unexpected_blocked:
            raise AssertionError(f"objective runtime has unexpected blocked requirements: {payload}")
        if "releasePackageReadiness" in blocked_ids:
            release_row = evidence.get("releasePackageReadiness") or {}
            if "/qa/beta-readiness-coverage" not in (release_row.get("routes") or []):
                raise AssertionError(f"objective runtime release blocker is missing beta readiness route: {payload}")
        if "l2DiskCacheStorageHit" in blocked_ids:
            raise AssertionError(f"objective runtime should use cache matrix contracts for ready L2 evidence: {payload}")
        if payload.get("knownGapCount", 0) < 1:
            raise AssertionError(f"objective runtime should surface known gaps: {payload}")
        if "qwenMultimodalRuntime" not in (payload.get("knownGapIds") or []):
            raise AssertionError(f"objective runtime missing qwen multimodal known gap: {payload}")
        if matrix.get("ok") is not True:
            raise AssertionError(f"objective flow requirement matrix route failed: {matrix}")
        if matrix.get("rowIds") != EXPECTED_REQUIREMENTS:
            raise AssertionError(f"objective flow matrix requirement order mismatch: {matrix}")
        if matrix.get("rowCount") != len(EXPECTED_REQUIREMENTS):
            raise AssertionError(f"objective flow matrix row count mismatch: {matrix}")
        if matrix.get("objectiveComplete") != payload.get("objectiveComplete"):
            raise AssertionError(f"objective flow matrix completion drift: {matrix}")
        if matrix.get("knownGapIds") != payload.get("knownGapIds"):
            raise AssertionError(f"objective flow matrix known gap drift: {matrix}")
        if matrix.get("rowProofFileParity") is not True or matrix.get("rowContractParity") is not True:
            raise AssertionError(f"objective flow matrix row parity mismatch: {matrix}")
        if matrix.get("liveArtifactParity") is not True:
            raise AssertionError(f"objective flow matrix live artifact parity mismatch: {matrix}")

        for name in EXPECTED_REQUIREMENTS:
            row = evidence.get(name) or {}
            if row.get("status") not in {"ready", "blocked", "tracked-known-gap"}:
                raise AssertionError(f"objective runtime requirement {name} has bad status: {payload}")
            if not row.get("routes"):
                raise AssertionError(f"objective runtime requirement {name} missing routes: {payload}")
            if not row.get("proofs"):
                raise AssertionError(f"objective runtime requirement {name} missing proofs: {payload}")
        if (evidence.get("l2DiskCacheStorageHit") or {}).get("status") != "ready":
            raise AssertionError(f"objective runtime L2 cache requirement should be ready: {payload}")
        if (evidence.get("cveDatabaseEmbeddings") or {}).get("status") != "ready":
            raise AssertionError(f"objective runtime CVE database/embedding requirement should be ready: {payload}")
        session_parallel = evidence.get("sessionParallelContinuousBatching") or {}
        if "/qa/live-loaded-model-agent-stress" not in (session_parallel.get("routes") or []):
            raise AssertionError(f"objective runtime session/parallel evidence missing live agent route: {payload}")
        if "live-loaded-model-agent-stress-proof.py" not in (session_parallel.get("proofs") or []):
            raise AssertionError(f"objective runtime session/parallel evidence missing live agent proof: {payload}")

        contracts = payload.get("contracts") or {}
        missing_contracts = sorted(name for name in EXPECTED_CONTRACTS if contracts.get(name) is not True)
        if missing_contracts:
            raise AssertionError(f"objective runtime missing contracts {missing_contracts}: {payload}")
        if payload.get("contractCount") != len(EXPECTED_CONTRACTS):
            raise AssertionError(f"objective runtime contract count mismatch: {payload}")
        if payload.get("contractParity") is not True:
            raise AssertionError(f"objective runtime contract parity mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"objective runtime proof-file parity mismatch: {payload}")

        state = request("GET", "/state")
        routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/objective-runtime-coverage" not in routes:
            raise AssertionError(f"state route list missing objective runtime coverage: {routes}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        release_group = (index.get("groups") or {}).get("releaseReadiness") or {}
        if "/qa/objective-runtime-coverage" not in (release_group.get("endpoints") or []):
            raise AssertionError(f"coverage index release group missing objective route: {release_group}")
        if "/qa/objective-flow-requirement-matrix" not in (release_group.get("endpoints") or []):
            raise AssertionError(f"coverage index release group missing objective flow matrix route: {release_group}")
        if release_group.get("objectiveRuntimeCoverageContractParity") is not True:
            raise AssertionError(f"coverage index missing objective parity: {release_group}")
        if release_group.get("objectiveRuntimeCoverageComplete") is not False:
            raise AssertionError(f"coverage index should not mark objective complete: {release_group}")
        if release_group.get("objectiveFlowRequirementRowCount") != matrix.get("rowCount"):
            raise AssertionError(f"coverage index objective flow matrix row count mismatch: {release_group}")
        if release_group.get("objectiveFlowRequirementLiveArtifactParity") != matrix.get("liveArtifactParity"):
            raise AssertionError(f"coverage index objective flow matrix live artifact parity mismatch: {release_group}")

        print("objective-runtime-coverage proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        print(f"objective-runtime-coverage proof failed: {exc}", flush=True)
        raise SystemExit(1)
