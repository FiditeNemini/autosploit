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
APP = ROOT / "release" / "ExploitBot.app"
APP_BINARY = APP / "Contents" / "MacOS" / "ExploitBot"
ENGINE_LAUNCH = APP / "Contents" / "Resources" / "ExploitBotEngine" / "launch.py"
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-release-engine-stale-cleanup.json"


def request_json(path: str, timeout: float = 5.0) -> dict[str, Any]:
    req = urllib.request.Request(f"{APP_API}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_state(timeout: float = 25.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            return request_json("/state", timeout=1.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"release app test server did not become ready: {last_error}")


def process_rows_containing(text: str, *, exclude_script: bool = True) -> list[str]:
    output = subprocess.check_output(["/bin/ps", "-axo", "pid=,command="], text=True)
    rows: list[str] = []
    for line in output.splitlines():
        if text not in line:
            continue
        if exclude_script and "release-engine-stale-cleanup-proof.py" in line:
            continue
        rows.append(line.strip())
    return rows


def pid_file_process_row(pid_file: Path) -> str | None:
    if not pid_file.exists():
        return None
    pid_text = "".join(ch for ch in pid_file.read_text(encoding="utf-8") if ch.isdigit())
    if not pid_text:
        return None
    try:
        output = subprocess.check_output(["/bin/ps", "-p", pid_text, "-o", "pid=,command="], text=True)
    except subprocess.CalledProcessError:
        return None
    rows = [line.strip() for line in output.splitlines() if line.strip()]
    return rows[0] if rows else None


def terminate(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_RELEASE_STALE_CLEANUP_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "release-engine-stale-cleanup-no-model-load",
        "app": str(APP),
        "engineLaunch": str(ENGINE_LAUNCH),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app_proc: subprocess.Popen[str] | None = None
    dummy_launch: subprocess.Popen[str] | None = None
    dummy_server: subprocess.Popen[str] | None = None
    temp_data = tempfile.TemporaryDirectory(prefix="exploitbot-release-cleanup-data-")
    pid_file = Path.home() / ".exploitbot" / "engine.pid"
    previous_pid_file = pid_file.read_text(encoding="utf-8") if pid_file.exists() else None
    error: Exception | None = None
    try:
        if not APP_BINARY.is_file():
            raise AssertionError(f"release app binary missing: {APP_BINARY}")
        if not ENGINE_LAUNCH.is_file():
            raise AssertionError(f"release bundled launch.py missing: {ENGINE_LAUNCH}")

        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        dummy_launch = subprocess.Popen(
            ["/usr/bin/python3", "-c", "import time; time.sleep(120)", str(ENGINE_LAUNCH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        dummy_server = subprocess.Popen(
            ["/usr/bin/python3", "-c", "import time; time.sleep(120)", "-m", "vmlx_engine.server", "--model", "dummy"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(f"{dummy_server.pid}\n", encoding="utf-8")
        time.sleep(0.25)

        before_launch_rows = process_rows_containing(str(ENGINE_LAUNCH))
        before_pid_row = pid_file_process_row(pid_file)
        report["beforeLaunchRows"] = before_launch_rows
        report["beforePidFileProcessRow"] = before_pid_row
        if not before_launch_rows:
            raise AssertionError("release dummy launch process was not visible in ps output")
        if before_pid_row is None or "vmlx_engine.server" not in before_pid_row:
            raise AssertionError(f"release dummy pidfile server was not visible in ps output: {before_pid_row}")

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_data.name) / ".exploitbot" / "data")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        app_proc = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env, text=True)
        state = wait_for_state()
        cleanup = state.get("engineStaleCleanup") or {}
        runtime = request_json("/qa/engine-python-runtime", timeout=5.0)
        after_launch_rows = process_rows_containing(str(ENGINE_LAUNCH))
        after_pid_row = pid_file_process_row(pid_file)

        report.update(
            {
                "ok": True,
                "state": state,
                "engineStaleCleanup": cleanup,
                "runtime": runtime,
                "afterLaunchRows": after_launch_rows,
                "afterPidFileProcessRow": after_pid_row,
                "dummyLaunchReturnCode": dummy_launch.poll(),
                "dummyServerReturnCode": dummy_server.poll(),
                "status": {
                    "releaseAppLaunched": "PASS",
                    "bundledLaunchCleanup": "PASS" if not after_launch_rows else "FAIL",
                    "pidFileServerCleanup": "PASS" if after_pid_row is None else "FAIL",
                    "bundledEnginePath": "PASS" if str(ENGINE_LAUNCH) in str(cleanup.get("launchScript") or "") else "FAIL",
                    "bundledRuntimeSelected": "PASS" if (runtime.get("selected") or {}).get("source") == "app-bundled-vmlx-python" else "FAIL",
                    "modelLoaded": "NO",
                },
            }
        )
        if cleanup.get("checked") is not True:
            raise AssertionError(f"release engine cleanup did not run: {cleanup}")
        if str(ENGINE_LAUNCH) not in str(cleanup.get("launchScript") or ""):
            raise AssertionError(f"release cleanup did not use bundled launch script: {cleanup}")
        if int(cleanup.get("foundCount") or 0) < 2:
            raise AssertionError(f"release cleanup did not find both dummy processes: {cleanup}")
        if int(cleanup.get("remainingCount") or 0) != 0:
            raise AssertionError(f"release cleanup left stale processes: {cleanup}")
        if after_launch_rows:
            raise AssertionError(f"release bundled launch dummy still visible: {after_launch_rows}")
        if after_pid_row is not None:
            raise AssertionError(f"release pidfile server dummy still visible: {after_pid_row}")
        if (runtime.get("selected") or {}).get("source") != "app-bundled-vmlx-python":
            raise AssertionError(f"release app did not select bundled runtime: {runtime}")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["state"] = request_json("/state", timeout=2.0)
        except Exception:
            pass
    finally:
        terminate(dummy_launch)
        terminate(dummy_server)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        terminate(app_proc)
        if previous_pid_file is None:
            try:
                pid_file.unlink()
            except FileNotFoundError:
                pass
        else:
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text(previous_pid_file, encoding="utf-8")
        temp_data.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("release-engine-stale-cleanup proof passed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"release-engine-stale-cleanup proof failed: {exc}", flush=True)
        raise SystemExit(1)
