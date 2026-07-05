#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
MODEL_ROOT = Path("/Users/eric/models/dealign.ai")
MODEL_27B = MODEL_ROOT / "Qwen3.6-27B-MXFP8-CRACK-MTP"
MODEL_35B = MODEL_ROOT / "Qwen3.6-35B-A3B-MXFP8-CRACK-MTP"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-settings-model-library-state.json"


def request(method: str, path: str, body: str | dict[str, Any] | None = None, timeout: float = 12.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_for_app(timeout: float = 20.0) -> None:
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


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:3000]
        raise AssertionError(message + suffix)


def entry_for(entries: list[dict[str, Any]], path: Path) -> dict[str, Any] | None:
    target = str(path)
    for entry in entries:
        if entry.get("path") == target:
            return entry
    return None


def select_and_capture(path: Path) -> dict[str, Any]:
    selected = request("POST", "/qa/model-folder-picker", {"action": "select", "path": str(path)})
    require(selected.get("ok") is True, f"select failed for {path}", selected)
    state = request("GET", "/state")
    engine = state.get("engineConfig") or {}
    picker = state.get("modelFolderPicker") or {}
    info = state.get("modelFolderInfo") or {}
    library = state.get("modelLibrary") or {}

    require(engine.get("modelPath") == str(path), "engineConfig modelPath did not update", engine)
    require(picker.get("selectedPath") == str(path), "picker selectedPath did not update", picker)
    require(picker.get("lastAction") == "select", "picker lastAction was not select", picker)
    require(picker.get("isVisible") is False, "picker remained visible after select", picker)
    require(info.get("path") == str(path), "modelFolderInfo path did not update", info)
    require(info.get("family") == "Qwen", "selected model family was not Qwen", info)
    require(info.get("isSupported") is True, "selected model is not supported", info)
    require(info.get("hasGenerationConfig") is True, "selected model lacks generation config", info)
    require(library.get("selectedPath") == str(path), "modelLibrary selectedPath did not update", library)
    return {
        "engineConfig": engine,
        "modelFolderPicker": picker,
        "modelFolderInfo": info,
        "modelLibrary": {
            "entryCount": library.get("entryCount"),
            "supportedCount": library.get("supportedCount"),
            "lastAction": library.get("lastAction"),
            "selectedPath": library.get("selectedPath"),
            "summary": library.get("summary"),
        },
    }


def run() -> None:
    output = Path(os.environ.get("EXPLOITBOT_SETTINGS_MODEL_LIBRARY_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "settings-model-library-state",
        "method": "live app API, no model load, isolated test home",
        "modelRoot": str(MODEL_ROOT),
        "models": {"qwen27": str(MODEL_27B), "qwen35": str(MODEL_35B)},
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app: subprocess.Popen[str] | None = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-settings-model-library-home-")
    try:
        require(MODEL_ROOT.is_dir(), f"model root missing: {MODEL_ROOT}")
        require(MODEL_27B.is_dir(), f"27B model folder missing: {MODEL_27B}")
        require(MODEL_35B.is_dir(), f"35B model folder missing: {MODEL_35B}")

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        if app.wait(timeout=45) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        opened = request("POST", "/qa/model-folder-picker", {"action": "open"})
        require(opened.get("ok") is True, "model folder picker open failed", opened)
        added = request("POST", "/qa/model-folder-picker", {"action": "addRoot", "path": str(MODEL_ROOT)})
        require(added.get("ok") is True, "model library addRoot failed", added)
        scanned = request("POST", "/qa/model-folder-picker", {"action": "scan"})
        require(scanned.get("ok") is True, "model library scan failed", scanned)

        state = request("GET", "/state")
        library = state.get("modelLibrary") or {}
        entries = library.get("entries") or []
        feed = state.get("feedRecent") or []
        qwen27 = entry_for(entries, MODEL_27B)
        qwen35 = entry_for(entries, MODEL_35B)
        report["scanState"] = {
            "roots": library.get("roots"),
            "entryCount": library.get("entryCount"),
            "supportedCount": library.get("supportedCount"),
            "lastAction": library.get("lastAction"),
            "summary": library.get("summary"),
            "qwen27Entry": qwen27,
            "qwen35Entry": qwen35,
            "feedRecent": feed[:8],
        }

        require(str(MODEL_ROOT) in (library.get("roots") or []), "model root was not persisted in state", library)
        require(library.get("lastAction") == "scan", "scan action was not recorded", library)
        require(isinstance(entries, list) and len(entries) >= 2, "model library did not expose entries", library)
        require(qwen27 is not None and qwen27.get("isSupported") is True, "27B MXFP8 MTP missing or unsupported", qwen27)
        require(qwen35 is not None and qwen35.get("isSupported") is True, "35B MXFP8 MTP missing or unsupported", qwen35)
        require(any("scanModelLibrary" in entry.get("text", "") for entry in feed), "scan action not visible in activity feed", feed)

        selected35 = select_and_capture(MODEL_35B)
        selected27 = select_and_capture(MODEL_27B)
        report["selected35"] = selected35
        report["selected27"] = selected27

        engine = selected27["engineConfig"]
        cache_status = {
            "q4KV": "PASS" if engine.get("kvCacheQuantization") == "turboquant-q4" else "FAIL",
            "prefixCache": "PASS" if engine.get("prefixCache") is True else "FAIL",
            "pagedCache": "PASS" if engine.get("pagedCache") is True else "FAIL",
            "promptL2Disk": "PASS" if engine.get("promptL2Disk") is True else "FAIL",
            "blockL2Disk": "PASS" if engine.get("blockL2Disk") is True else "FAIL",
            "generationDefaultsToggleVisibleInState": "PASS" if "useModelGenerationDefaults" in engine else "FAIL",
        }
        status = {
            "addRoot": "PASS",
            "scan": "PASS",
            "qwen27Visible": "PASS",
            "qwen35Visible": "PASS",
            "qwen35Selectable": "PASS",
            "qwen27Selectable": "PASS",
            "activityFeedScanVisible": "PASS",
            **cache_status,
            "noModelLoaded": "PASS" if state.get("engineRunning") is False else "FAIL",
        }
        report["status"] = status
        if any(value != "PASS" for value in status.values()):
            raise AssertionError(f"settings model library state proof failed status checks: {status}")

        report["ok"] = True
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        temp_home.cleanup()

    print(f"settings model-library state proof wrote {output}")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"settings model-library state proof failed: {exc}", flush=True)
        raise SystemExit(1)
