#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "scripts" / "release-app-live-qwen-proof.py"
ARTIFACT = ROOT / "docs" / "live-proofs" / "2026-07-05-release-qwen-memory-preflight-current.json"
MODELS = [
    ROOT / "docs/live-proofs/2026-07-05-release-app-live-qwen-27b-current.json",
    ROOT / "docs/live-proofs/2026-07-05-release-app-live-qwen-35b-current.json",
]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_release_qwen_module():
    spec = importlib.util.spec_from_file_location("release_app_live_qwen_proof", PROOF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model_paths_from_current_artifacts() -> list[Path]:
    paths: list[Path] = []
    for artifact in MODELS:
        data = json.loads(artifact.read_text(encoding="utf-8"))
        model = data.get("model")
        if model:
            paths.append(Path(model))
    return paths


def row_for_model(module: Any, model: Path) -> dict[str, Any]:
    try:
        preflight = module.release_qwen_memory_preflight(model)
        status = "PASS"
    except module.ReleaseQwenMemoryPreflightError as exc:
        preflight = exc.report
        status = "BLOCKED"
    return {
        "model": str(model),
        "status": status,
        "memoryPreflight": preflight,
    }


def main() -> None:
    module = load_release_qwen_module()
    rows = [row_for_model(module, model) for model in model_paths_from_current_artifacts()]
    status_counts = {
        "PASS": sum(1 for row in rows if row["status"] == "PASS"),
        "BLOCKED": sum(1 for row in rows if row["status"] == "BLOCKED"),
    }
    report = {
        "ok": True,
        "proofType": "release-qwen-memory-preflight-current",
        "generatedAt": timestamp(),
        "proofLevel": "no-model-load-release-qwen-memory-preflight",
        "sourceScript": str(PROOF.relative_to(ROOT)),
        "modelRows": rows,
        "statusCounts": status_counts,
        "overallStatus": "BLOCKED" if status_counts["BLOCKED"] else "PASS",
        "modelLoadAttempted": False,
        "nextAction": (
            "wait for heavyweight vllm/model/eval jobs to exit or set EXPLOITBOT_RELEASE_QWEN_ALLOW_CONCURRENT_MODEL=1 intentionally"
            if status_counts["BLOCKED"]
            else "safe to run bounded release-app-live-qwen-proof.py"
        ),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"release Qwen memory preflight proof wrote {ARTIFACT} status={report['overallStatus']}")


if __name__ == "__main__":
    main()
