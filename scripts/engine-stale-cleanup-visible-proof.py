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
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ENGINE_LAUNCH = ROOT / "ExploitBotEngine" / "launch.py"
ENGINE_PID_FILE = Path.home() / ".exploitbot" / "engine.pid"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-engine-stale-cleanup-visible.json"


def request_json(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_state(timeout: float = 25.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            return request_json("GET", "/state", timeout=1.0)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            last_error = exc
            time.sleep(0.25)
    raise AssertionError(f"app test server did not become ready: {last_error}")


def matching_launch_processes() -> list[str]:
    output = subprocess.check_output(["/bin/ps", "-axo", "pid=,command="], text=True)
    return [
        line.strip()
        for line in output.splitlines()
        if str(ENGINE_LAUNCH) in line and "engine-stale-cleanup-visible-proof.py" not in line
    ]


def pid_file_process_row() -> str | None:
    if not ENGINE_PID_FILE.exists():
        return None
    pid_text = "".join(ch for ch in ENGINE_PID_FILE.read_text(encoding="utf-8") if ch.isdigit())
    if not pid_text:
        return None
    try:
        output = subprocess.check_output(["/bin/ps", "-p", pid_text, "-o", "pid=,command="], text=True)
    except subprocess.CalledProcessError:
        return None
    rows = [line.strip() for line in output.splitlines() if line.strip()]
    return rows[0] if rows else None


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_STALE_CLEANUP_VISIBLE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": False,
        "proofType": "engine-stale-cleanup-visible-no-model-load",
        "engineLaunch": str(ENGINE_LAUNCH),
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    app: subprocess.Popen[str] | None = None
    dummy: subprocess.Popen[str] | None = None
    dummy_pid_server: subprocess.Popen[str] | None = None
    app_home = tempfile.TemporaryDirectory(prefix="exploitbot-stale-cleanup-home-")
    previous_pid_file = ENGINE_PID_FILE.read_text(encoding="utf-8") if ENGINE_PID_FILE.exists() else None
    error: Exception | None = None
    try:
        subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT, check=True)
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        dummy = subprocess.Popen(
            ["/usr/bin/python3", "-c", "import time; time.sleep(120)", str(ENGINE_LAUNCH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        time.sleep(0.25)
        before = matching_launch_processes()
        report["beforeLaunchProcessRows"] = before
        if not before:
            raise AssertionError("dummy stale engine process was not visible in ps output")

        dummy_pid_server = subprocess.Popen(
            ["/usr/bin/python3", "-c", "import time; time.sleep(120)", "-m", "vmlx_engine.server", "--model", "dummy"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        ENGINE_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENGINE_PID_FILE.write_text(f"{dummy_pid_server.pid}\n", encoding="utf-8")
        time.sleep(0.25)
        before_pid_row = pid_file_process_row()
        report["beforePidFileProcessRow"] = before_pid_row
        if before_pid_row is None or "vmlx_engine.server" not in before_pid_row:
            raise AssertionError(f"dummy pidfile server was not visible in ps output: {before_pid_row}")

        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["EXPLOITBOT_DATA_DIR"] = str(Path(app_home.name) / ".exploitbot" / "data")
        app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env, text=True)
        state = wait_for_state()
        cleanup = state.get("engineStaleCleanup") or {}
        after = matching_launch_processes()
        after_pid_row = pid_file_process_row()

        report.update(
            {
                "ok": True,
                "state": state,
                "engineStaleCleanup": cleanup,
                "afterLaunchProcessRows": after,
                "afterPidFileProcessRow": after_pid_row,
                "dummyReturnCode": dummy.poll(),
                "dummyPidFileServerReturnCode": dummy_pid_server.poll() if dummy_pid_server else None,
                "status": {
                    "stateVisibleStaleCleanup": "PASS",
                    "dummyStaleProcessRemoved": "PASS" if not after else "FAIL",
                    "dummyPidFileServerRemoved": "PASS" if after_pid_row is None else "FAIL",
                    "modelLoaded": "NO",
                },
            }
        )
        if cleanup.get("checked") is not True:
            raise AssertionError(f"engineStaleCleanup did not report checked=true: {cleanup}")
        if int(cleanup.get("foundCount") or 0) < 1:
            raise AssertionError(f"engineStaleCleanup did not report the dummy process: {cleanup}")
        if int(cleanup.get("remainingCount") or 0) != 0:
            raise AssertionError(f"engineStaleCleanup left stale processes: {cleanup}")
        if cleanup.get("cleaned") is not True:
            raise AssertionError(f"engineStaleCleanup did not mark cleaned=true: {cleanup}")
        if after:
            raise AssertionError(f"stale launch.py process still visible after app startup cleanup: {after}")
        if after_pid_row is not None:
            raise AssertionError(f"stale pidfile server process still visible after app startup cleanup: {after_pid_row}")
        if dummy.poll() is None:
            raise AssertionError("dummy stale engine process is still running")
        if dummy_pid_server is not None and dummy_pid_server.poll() is None:
            raise AssertionError("dummy pidfile server process is still running")
    except Exception as exc:
        error = exc
        report.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        try:
            report["state"] = request_json("GET", "/state", timeout=2.0)
        except Exception:
            pass
    finally:
        if dummy is not None and dummy.poll() is None:
            dummy.terminate()
            try:
                dummy.wait(timeout=2)
            except subprocess.TimeoutExpired:
                dummy.kill()
        if dummy_pid_server is not None and dummy_pid_server.poll() is None:
            dummy_pid_server.terminate()
            try:
                dummy_pid_server.wait(timeout=2)
            except subprocess.TimeoutExpired:
                dummy_pid_server.kill()
        if previous_pid_file is None:
            try:
                ENGINE_PID_FILE.unlink()
            except FileNotFoundError:
                pass
        else:
            ENGINE_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            ENGINE_PID_FILE.write_text(previous_pid_file, encoding="utf-8")
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
        app_home.cleanup()
        report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error is not None:
        raise error
    print("engine-stale-cleanup-visible proof passed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"engine-stale-cleanup-visible proof failed: {exc}", flush=True)
        raise SystemExit(1)
