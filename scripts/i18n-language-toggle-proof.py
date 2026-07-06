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

from app_proof_lock import app_proof_lock


ROOT = Path(__file__).resolve().parents[1]
APP_API = "http://127.0.0.1:9999"
APP_BINARY = ROOT / "dist" / "ExploitBot.app" / "Contents" / "MacOS" / "ExploitBot"
ARTIFACT = ROOT / "docs/live-proofs/2026-07-06-i18n-language-toggle.json"
LANGUAGE_PROOF_SEQUENCE = [{"language": "es"}, {"language": "ja"}]


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request(method: str, path: str, body: dict[str, Any] | str | None = None, timeout: float = 8.0) -> Any:
    if isinstance(body, dict):
        body = json.dumps(body)
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request(f"{APP_API}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def wait_until(predicate, label: str, timeout: float = 30.0) -> Any:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            last = None
        if last:
            return last
        time.sleep(0.25)
    raise AssertionError(f"timed out waiting for {label}: {last}")


def build_app_bundle() -> None:
    result = subprocess.run([str(ROOT / "script" / "build_and_run.sh"), "--build-only"], cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError("build_and_run --build-only failed")
    if not APP_BINARY.exists():
        raise RuntimeError(f"app binary missing after build: {APP_BINARY}")


def passfail(value: bool) -> str:
    return "PASS" if value else "FAIL"


def complete_onboarding(language: str) -> dict[str, Any]:
    return request(
        "POST",
        "/qa/onboarding-complete",
        {
            "language": language,
            "modelPath": "",
            "opName": f"QA i18n {language}",
            "mode": "manual",
            "scope": "127.0.0.1",
            "startEngine": False,
        },
        timeout=10.0,
    )


def build_report(started_at: str, snapshots: dict[str, dict[str, Any]], state_after: dict[str, Any]) -> dict[str, Any]:
    en = snapshots["en"]
    es = snapshots["es"]
    ja = snapshots["ja"]
    checks = {
        "supportedLanguages": passfail(en.get("supportedLanguages") == ["en", "ko", "zh", "es", "ja"]),
        "languageToggleSpanish": passfail(es.get("currentLanguage") == "es"),
        "languageToggleJapanese": passfail(ja.get("currentLanguage") == "ja"),
        "tabLabelsChanged": passfail(
            en.get("tabs", {}).get("network") == "Network"
            and es.get("tabs", {}).get("network") == "Red"
            and ja.get("tabs", {}).get("network") == "ネットワーク"
            and es.get("tabs", {}).get("supplyChain") == "Suministro"
        ),
        "toolLabelsPresent": passfail(
            es.get("tools", {}).get("run_shell") == "Ejecutar shell"
            and ja.get("tools", {}).get("run_shell") == "シェル実行"
            and es.get("tools", {}).get("search_cve") == "Buscar CVE"
            and ja.get("tools", {}).get("search_cve") == "CVE検索"
            and es.get("tools", {}).get("httpx") == "httpx"
        ),
        "coreLabelsChanged": passfail(
            en.get("core", {}).get("settings") == "Settings"
            and es.get("core", {}).get("settings") == "Configuración"
            and ja.get("core", {}).get("settings") == "設定"
            and es.get("core", {}).get("chatApprove") == "Aprobar"
            and ja.get("core", {}).get("chatApprove") == "承認"
        ),
        "noModelLoaded": passfail(state_after.get("engineRunning") is False and not state_after.get("model")),
    }
    ok = all(value == "PASS" for value in checks.values())
    return {
        "ok": ok,
        "proofType": "i18n-language-toggle-live-app",
        "proofLevel": "live-app-qa-route-language-toggle-no-model-load",
        "status": "PASS" if ok else "FAIL",
        "startedAt": started_at,
        "finishedAt": timestamp(),
        "checks": checks,
        "snapshots": snapshots,
        "stateAfter": state_after,
        "notes": [
            "This verifies the app language state and localized labels through live QA routes.",
            "It does not prove every visible SwiftUI Text has been converted from hard-coded strings yet.",
        ],
    }


def run() -> None:
    started_at = timestamp()
    app = None
    temp_home = tempfile.TemporaryDirectory(prefix="exploitbot-i18n-home-", ignore_cleanup_errors=True)
    report: dict[str, Any] = {"ok": False, "proofType": "i18n-language-toggle-live-app", "startedAt": started_at}
    error: Exception | None = None
    try:
        env = os.environ.copy()
        env["EXPLOITBOT_TESTING"] = "1"
        env["HOME"] = temp_home.name
        env["EXPLOITBOT_DATA_DIR"] = str(Path(temp_home.name) / ".exploitbot" / "data")

        with app_proof_lock("i18n-language-toggle-proof.py"):
            subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            build_app_bundle()
            app = subprocess.Popen([str(APP_BINARY)], cwd=ROOT, env=env)
            wait_until(lambda: request("GET", "/state", timeout=1.0), "app test server")

            snapshots: dict[str, dict[str, Any]] = {
                "en": request("GET", "/qa/i18n-snapshot", timeout=5.0),
            }
            for row in LANGUAGE_PROOF_SEQUENCE:
                language = row["language"]
                response = complete_onboarding(language)
                if response.get("ok") is not True:
                    raise AssertionError(f"onboarding language toggle failed for {language}: {response}")
                snapshots[language] = request("GET", "/qa/i18n-snapshot", timeout=5.0)
            state_after = request("GET", "/state", timeout=5.0)
            report = build_report(started_at, snapshots, state_after)
            if not report["ok"]:
                raise AssertionError("i18n language toggle checks failed", report["checks"])
    except Exception as exc:
        error = exc
        report.update({"ok": False, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "finishedAt": timestamp()})
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app is not None and app.poll() is None:
            app.send_signal(signal.SIGTERM)
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
        temp_home.cleanup()
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if error:
        raise error
    print(f"i18n language toggle proof passed: {ARTIFACT}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"i18n language toggle proof failed: {exc}", flush=True)
        raise SystemExit(1)
