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
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
THEME_ROOT = ROOT / "ExploitBot" / "Sources" / "ExploitBot" / "Theme"

EXPECTED_GROUPS = [
    "actionButtons",
    "branding",
    "colorTokens",
    "overlays",
    "controls",
    "clipboard",
    "typography",
    "navigationControls",
]

EXPECTED_PROOFS = [
    "theme-inventory-proof.py",
    "visual-coverage-proof.py",
    "settings-coverage-proof.py",
    "app-qa-matrix-smoke-proof.py",
]

REQUIRED_COLOR_TOKENS = [
    "bgDeep",
    "bgBase",
    "bgRaised",
    "bgSurface",
    "bgInput",
    "borderSubtle",
    "borderMedium",
    "borderStrong",
    "textPrimary",
    "textSecondary",
    "textMuted",
    "accentBlue",
    "accentGreen",
    "accentRed",
]


def theme_files() -> list[Path]:
    return sorted(THEME_ROOT.glob("*.swift"))


def group_for(path: Path) -> str:
    return {
        "AccentActionButton.swift": "actionButtons",
        "BotIcon.swift": "branding",
        "Colors.swift": "colorTokens",
        "ConfirmationSheet.swift": "overlays",
        "Controls.swift": "controls",
        "CopyButton.swift": "clipboard",
        "Fonts.swift": "typography",
        "SubtabBar.swift": "navigationControls",
    }.get(path.name, "controls")


def proof_for(group: str) -> str:
    return {
        "colorTokens": "visual-coverage-proof.py",
        "typography": "visual-coverage-proof.py",
        "controls": "settings-coverage-proof.py",
        "navigationControls": "visual-coverage-proof.py",
        "actionButtons": "visual-coverage-proof.py",
        "clipboard": "app-qa-matrix-smoke-proof.py",
        "branding": "visual-coverage-proof.py",
        "overlays": "visual-coverage-proof.py",
    }[group]


def parse_file(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(ROOT))
    group = group_for(path)
    types = [
        {"kind": kind, "name": name}
        for kind, name in re.findall(r"^\s*(struct|class|enum|protocol|extension)\s+([A-Za-z_][A-Za-z0-9_]*)", source, flags=re.MULTILINE)
    ]
    functions = re.findall(
        r"^\s*(?:private\s+|static\s+|@MainActor\s+|mutating\s+|nonisolated\s+|override\s+|class\s+|final\s+)*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        source,
        flags=re.MULTILINE,
    )
    static_tokens = re.findall(
        r"^\s*static\s+(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)",
        source,
        flags=re.MULTILINE,
    )
    corner_radii = [
        float(value)
        for value in re.findall(r"cornerRadius:\s*([0-9]+(?:\.[0-9]+)?)", source)
    ]
    return {
        "file": rel,
        "group": group,
        "proofOwner": proof_for(group),
        "types": types,
        "typeCount": len(types),
        "functions": functions,
        "functionCount": len(functions),
        "staticTokens": static_tokens,
        "staticTokenCount": len(static_tokens),
        "cornerRadii": corner_radii,
        "maxCornerRadius": max(corner_radii) if corner_radii else 0,
    }


def source_inventory() -> list[dict[str, object]]:
    return [parse_file(path) for path in theme_files()]


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

        inventory = source_inventory()
        payload = request("GET", "/qa/theme-inventory")
        if payload.get("ok") is not True:
            raise AssertionError(f"theme inventory route failed: {payload}")
        if payload.get("sourceRoot") != "ExploitBot/Sources/ExploitBot/Theme":
            raise AssertionError(f"theme inventory source root mismatch: {payload}")
        if payload.get("files") != inventory:
            raise AssertionError(f"theme inventory file list mismatch: {payload}")
        if payload.get("fileCount") != len(inventory):
            raise AssertionError(f"theme inventory file count mismatch: {payload}")
        if payload.get("typeCount") != sum(item["typeCount"] for item in inventory):
            raise AssertionError(f"theme inventory type count mismatch: {payload}")
        if payload.get("functionCount") != sum(item["functionCount"] for item in inventory):
            raise AssertionError(f"theme inventory function count mismatch: {payload}")
        if payload.get("staticTokenCount") != sum(item["staticTokenCount"] for item in inventory):
            raise AssertionError(f"theme inventory static token count mismatch: {payload}")
        if payload.get("maxCornerRadius", 0) > 8:
            raise AssertionError(f"theme inventory corner radius policy mismatch: {payload}")

        if payload.get("groups") != EXPECTED_GROUPS:
            raise AssertionError(f"theme inventory groups mismatch: {payload}")
        expected_counts = dict(Counter(item["group"] for item in inventory))
        expected_counts = {group: expected_counts.get(group, 0) for group in EXPECTED_GROUPS}
        if payload.get("groupCounts") != expected_counts:
            raise AssertionError(f"theme inventory group counts mismatch: {payload}")

        tokens = payload.get("staticTokens") or []
        missing_tokens = [token for token in REQUIRED_COLOR_TOKENS if token not in tokens]
        if missing_tokens:
            raise AssertionError(f"theme inventory missing color tokens {missing_tokens}: {payload}")
        if payload.get("professionalShapePolicy") != "max-corner-radius-8":
            raise AssertionError(f"theme inventory shape policy mismatch: {payload}")

        state = request("GET", "/state")
        state_routes = (state.get("qaCoverage") or {}).get("stateRoutes") or []
        if "/qa/theme-inventory" not in state_routes:
            raise AssertionError(f"state route list missing theme inventory route: {state_routes}")

        index = request("GET", "/qa/coverage-index", timeout=120.0)
        visual_group = (index.get("groups") or {}).get("settingsAndVisuals") or {}
        if visual_group.get("themeInventoryFileCount") != payload.get("fileCount"):
            raise AssertionError(f"coverage index theme file count mismatch: {index}")
        if visual_group.get("themeInventoryTypeCount") != payload.get("typeCount"):
            raise AssertionError(f"coverage index theme type count mismatch: {index}")
        if visual_group.get("themeInventoryStaticTokenCount") != payload.get("staticTokenCount"):
            raise AssertionError(f"coverage index theme static token count mismatch: {index}")
        if visual_group.get("themeInventoryGroupCounts") != payload.get("groupCounts"):
            raise AssertionError(f"coverage index theme group count mismatch: {index}")
        if visual_group.get("themeInventoryProofFileParity") != payload.get("proofFileParity"):
            raise AssertionError(f"coverage index theme proof parity mismatch: {index}")

        proofs = payload.get("proofs") or []
        if proofs != EXPECTED_PROOFS:
            raise AssertionError(f"theme inventory proof list mismatch: {payload}")
        if payload.get("proofCount") != len(EXPECTED_PROOFS):
            raise AssertionError(f"theme inventory proof count mismatch: {payload}")
        if payload.get("proofFileParity") is not True:
            raise AssertionError(f"theme inventory proof-file parity mismatch: {payload}")

        print("theme-inventory proof passed")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, RuntimeError, urllib.error.URLError, TimeoutError, socket.timeout, subprocess.CalledProcessError) as exc:
        print(f"theme-inventory proof failed: {exc}", flush=True)
        raise SystemExit(1)
