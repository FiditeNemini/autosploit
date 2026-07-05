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


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-tool-settings-real-inventory.json"
REAL_LOOPBACK_TOOLS = {"curl", "nc", "python3"}
PENTEST_TOOLS = {"nmap", "httpx", "nuclei", "sqlmap", "hydra", "metasploit", "netexec", "linpeas"}


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0):
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


def tool_maps(settings: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    tools = settings.get("tools") or []
    by_name = {str(tool.get("name")): tool for tool in tools}
    missing_pentest = sorted(
        tool for tool in PENTEST_TOOLS
        if (by_name.get(tool) or {}).get("status") != "installed"
    )
    error_pentest = sorted(
        tool for tool in PENTEST_TOOLS
        if (by_name.get(tool) or {}).get("status") == "error"
    )
    return by_name, missing_pentest, error_pentest


def run() -> None:
    output = Path(os.environ.get("EXPLOITBOT_TOOL_INVENTORY_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "tool-settings-real-current-machine-inventory",
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app = None
    error: Exception | None = None
    try:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = subprocess.Popen([str(ROOT / "script" / "build_and_run.sh"), "--verify"], cwd=ROOT, env=env)
        if app.wait(timeout=45) != 0:
            raise RuntimeError("build_and_run --verify failed")
        wait_for_app()

        response = request("POST", "/qa/tool-settings-action", {"action": "detectCurrentMachine"})
        if response.get("ok") is not True:
            raise AssertionError(f"detectCurrentMachine action failed: {response}")

        state = request("GET", "/state")
        settings = state.get("toolSettings") or {}
        actions = state.get("toolSettingsActions") or {}
        by_name, missing_pentest, error_pentest = tool_maps(settings)
        installed_real = {
            name: by_name[name]
            for name in sorted(REAL_LOOPBACK_TOOLS)
            if (by_name.get(name) or {}).get("status") == "installed"
        }

        if actions.get("lastAction") != "detectCurrentMachine" or actions.get("status") != "done":
            raise AssertionError(f"action state did not record current detection: {actions}")
        if "detectCurrentMachine" not in str(settings.get("installLog") or ""):
            raise AssertionError(f"install log missing current detection marker: {settings}")
        if not {"curl", "nc"}.issubset(installed_real):
            raise AssertionError(f"real loopback tools missing from app tool settings: {installed_real}")

        report.update(
            {
                "ok": True,
                "toolSettings": settings,
                "toolSettingsActions": actions,
                "installedLoopbackTools": installed_real,
                "missingPentestTools": missing_pentest,
                "errorPentestTools": error_pentest,
                "installedCount": settings.get("installedCount"),
                "missingCount": settings.get("missingCount"),
                "status": {
                    "settingsCurrentMachineDetection": "PASS",
                    "fullPentestToolchainInstalled": "PASS" if not missing_pentest else "PARTIAL",
                },
            }
        )
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["state"] = request("GET", "/state", timeout=3.0)
        except Exception:
            pass
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("tool-settings-real-inventory proof passed")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"tool-settings-real-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
