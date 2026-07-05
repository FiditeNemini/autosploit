#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = Path("/Users/eric/.codex/plugins/cache/openai-bundled/computer-use/1.0.857")
SERVICE_APP = PLUGIN_ROOT / "Codex Computer Use.app"
CLIENT = SERVICE_APP / "Contents/SharedSupport/SkyComputerUseClient.app/Contents/MacOS/SkyComputerUseClient"
SHIM = PLUGIN_ROOT / "mcp-framing-shim.py"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-computer-use-transport-blocked.json"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd: list[str], timeout: float = 10.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "timeout": timeout,
            "stdout": (exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
        }


def filtered_processes(*needles: str) -> str:
    proc = subprocess.run(
        ["/bin/ps", "axo", "pid,ppid,stat,rss,vsz,etime,command"],
        text=True,
        capture_output=True,
        timeout=10.0,
    )
    lines = []
    for line in proc.stdout.splitlines():
        if any(needle in line for needle in needles):
            lines.append(line)
    return "\n".join(lines)


def direct_client(messages: list[dict[str, Any]], timeout: float = 8.0, keep_open: bool = False) -> dict[str, Any]:
    proc = subprocess.Popen(
        [str(CLIENT), "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    for msg in messages:
        proc.stdin.write(json.dumps(msg, separators=(",", ":")) + "\n")
        proc.stdin.flush()
        time.sleep(0.1)
    if not keep_open:
        proc.stdin.close()

    lines: list[str] = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        ready, _, _ = select.select([proc.stdout], [], [], 0.25)
        if ready:
            line = proc.stdout.readline()
            if line:
                lines.append(line.rstrip("\n"))

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)

    remainder = proc.stdout.read()
    if remainder:
        lines.extend(line for line in remainder.splitlines() if line)
    stderr = proc.stderr.read()
    return {
        "returncode": proc.returncode,
        "lineCount": len(lines),
        "lines": lines,
        "stderr": stderr[-12000:],
        "sawInitialize": any('"id":1' in line for line in lines),
        "sawToolResponse": any('"id":2' in line for line in lines),
    }


def frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def shim_tools_list(timeout: float = 8.0) -> dict[str, Any]:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "exploitbot-computer-use-proof", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    payload = b"".join(frame(msg) for msg in messages)
    try:
        proc = subprocess.run(
            ["python3", str(SHIM)],
            input=payload,
            capture_output=True,
            timeout=timeout,
            cwd=str(PLUGIN_ROOT),
        )
        stdout = proc.stdout.decode("utf-8", "replace")
        stderr = proc.stderr.decode("utf-8", "replace")
        return {
            "returncode": proc.returncode,
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
            "sawInitialize": '"id":1' in stdout,
            "sawToolsList": '"tools"' in stdout and '"list_apps"' in stdout,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace")
        stderr = (exc.stderr or b"").decode("utf-8", "replace")
        return {"timeout": timeout, "stdout": stdout[-12000:], "stderr": stderr[-12000:]}


def read_frame(stdout, proc: subprocess.Popen[bytes], timeout: float) -> str | None:
    deadline = time.time() + timeout
    data = b""
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        ready, _, _ = select.select([stdout], [], [], 0.25)
        if not ready:
            continue
        chunk = os.read(stdout.fileno(), 4096)
        if not chunk:
            break
        data += chunk
        sep = b"\r\n\r\n" if b"\r\n\r\n" in data else (b"\n\n" if b"\n\n" in data else None)
        if sep is None:
            continue
        header, rest = data.split(sep, 1)
        content_length: int | None = None
        for line in header.splitlines():
            if line.lower().startswith(b"content-length:"):
                content_length = int(line.split(b":", 1)[1])
                break
        if content_length is None:
            return None
        while len(rest) < content_length:
            rest += os.read(stdout.fileno(), content_length - len(rest))
        return rest[:content_length].decode("utf-8", "replace")
    return None


def shim_list_apps_call(timeout: float = 15.0) -> dict[str, Any]:
    proc = subprocess.Popen(
        ["python3", str(SHIM)],
        cwd=str(PLUGIN_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    result: dict[str, Any] = {}
    try:
        init = base_initialize()
        proc.stdin.write(frame(init))
        proc.stdin.flush()
        initialize_response = read_frame(proc.stdout, proc, timeout=5.0)
        proc.stdin.write(frame({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}))
        proc.stdin.write(frame({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_apps", "arguments": {}}}))
        proc.stdin.flush()
        tool_response = read_frame(proc.stdout, proc, timeout=timeout)
        result = {
            "returncodeBeforeTerminate": proc.poll(),
            "sawInitialize": initialize_response is not None and '"id":1' in initialize_response,
            "initializeResponse": initialize_response or "",
            "sawToolResponse": tool_response is not None and '"id":2' in tool_response,
            "toolResponse": tool_response or "",
        }
        return result
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        stderr = proc.stderr.read().decode("utf-8", "replace")
        result["stderr"] = stderr[-12000:]


def tool_call_status(result: dict[str, Any]) -> str:
    if not result.get("sawToolResponse"):
        return "FAIL_NO_TOOL_RESPONSE"
    response = result.get("toolResponse") or "\n".join(result.get("lines") or [])
    if '"isError":true' in response or '"isError": true' in response:
        if "Computer Use server error -10000" in response or "Sender process is not authenticated" in response:
            return "FAIL_AUTHENTICATION_ERROR"
        return "FAIL_TOOL_ERROR_RESPONSE"
    return "PASS"


def base_initialize() -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "exploitbot-computer-use-proof", "version": "0"},
        },
    }


def main() -> None:
    output = Path(os.environ.get("EXPLOITBOT_COMPUTER_USE_OUTPUT", str(DEFAULT_OUTPUT))).expanduser()
    report: dict[str, Any] = {
        "ok": True,
        "proofType": "computer-use-transport-current-state",
        "startedAt": now(),
        "pluginRoot": str(PLUGIN_ROOT),
        "serviceApp": str(SERVICE_APP),
        "client": str(CLIENT),
        "shim": str(SHIM),
        "note": "This proof does not call the active Codex MCP tool; the live tool call in-chat returned Transport closed immediately.",
    }

    subprocess.run(["open", "-a", str(SERVICE_APP)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    report["codesignVerify"] = run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(SERVICE_APP)])
    report["serviceEntitlements"] = run(["/usr/bin/codesign", "-d", "--entitlements", ":-", str(SERVICE_APP)])
    report["clientEntitlements"] = run(["/usr/bin/codesign", "-d", "--entitlements", ":-", str(CLIENT.parent.parent.parent)])
    report["computerUseProcesses"] = {
        "stdout": filtered_processes("SkyComputerUse", "mcp-framing-shim", "Codex Computer Use")
    }
    report["socketFiles"] = run(
        [
            "/usr/bin/find",
            "/Users/eric/Library/Group Containers/2DC432GLL2.com.openai.sky.CUAService",
            "-maxdepth",
            "4",
            "(",
            "-type",
            "s",
            "-o",
            "-name",
            "computeruse.sock*",
            ")",
            "-print",
        ]
    )
    report["memoryPressure"] = run(["/usr/bin/memory_pressure"])
    report["vmStat"] = run(["/usr/bin/vm_stat"])
    report["topRSSProcesses"] = run(["/bin/ps", "axo", "pid,ppid,stat,rss,vsz,etime,command"])
    report["topRSSProcesses"]["stdout"] = "\n".join(
        sorted(report["topRSSProcesses"].get("stdout", "").splitlines()[1:], key=lambda line: int(line.split()[3]), reverse=True)[:25]
    )

    init = base_initialize()
    report["directToolsList"] = direct_client([init, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}], timeout=8.0)
    report["directListAppsCallHeldOpen"] = direct_client(
        [
            init,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_apps", "arguments": {}}},
        ],
        timeout=15.0,
        keep_open=True,
    )
    report["shimToolsList"] = shim_tools_list()
    report["shimListAppsCallHeldOpen"] = shim_list_apps_call()
    report["recentComputerUseLogs"] = run(
        [
            "/usr/bin/log",
            "show",
            "--style",
            "compact",
            "--last",
            "5m",
            "--predicate",
            'process == "SkyComputerUseClient" OR process == "SkyComputerUseService" OR eventMessage CONTAINS "TCC" OR eventMessage CONTAINS "AppleEvents" OR eventMessage CONTAINS "Computer Use"',
        ],
        timeout=15.0,
    )

    report["status"] = {
        "activeCodexMCP": "BLOCKED_TRANSPORT_CLOSED",
        "serviceRunning": "PASS" if "SkyComputerUseService" in report["computerUseProcesses"].get("stdout", "") else "FAIL",
        "serviceSocket": "PASS" if "computeruse.sock" in report["socketFiles"].get("stdout", "") else "FAIL",
        "directToolsList": "PASS" if report["directToolsList"].get("sawToolResponse") else "FAIL",
        "shimToolsList": "PASS" if report["shimToolsList"].get("sawToolsList") else "FAIL",
        "shimListAppsToolCall": tool_call_status(report["shimListAppsCallHeldOpen"]),
        "directListAppsToolCall": tool_call_status(report["directListAppsCallHeldOpen"]),
        "currentMemoryPressure": "PASS_NOT_REPRODUCED" if "System-wide memory free percentage" in report["memoryPressure"].get("stdout", "") else "UNKNOWN",
    }
    report["finishedAt"] = now()
    report["generatedAt"] = report["finishedAt"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"computer-use transport proof wrote {output}")


if __name__ == "__main__":
    main()
