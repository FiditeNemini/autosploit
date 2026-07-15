#!/usr/bin/env python3
from __future__ import annotations

import plistlib
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script" / "package_release.sh"
APP = ROOT / "release" / "ExploitBot.app"
DMG = ROOT / "release" / "ExploitBot.dmg"
MANIFEST = ROOT / "release" / "release-manifest.json"
ENTITLEMENTS = ROOT / "ExploitBot" / "ExploitBot.entitlements"
APP_API = "http://127.0.0.1:9999"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-release-readiness.json"
EXPECTED_VERSION = os.environ.get("EXPLOITBOT_RELEASE_VERSION", "1.5.2")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run_no_bytecode(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)


def require(condition: bool, message: str, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{message}\n{detail}".strip())


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def request(path: str, timeout: float = 8.0):
    req = urllib.request.Request(f"{APP_API}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_app(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request("/state", timeout=1.0)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"release app test server did not become ready: {last_error}")


def assert_release_app_uses_bundled_runtime() -> str:
    subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {**os.environ, "EXPLOITBOT_TESTING": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    app = subprocess.Popen([str(APP / "Contents" / "MacOS" / "ExploitBot")], cwd=ROOT, env=env)
    try:
        wait_for_app()
        payload = request("/qa/engine-python-runtime")
        require(payload.get("ok") is True, f"release app engine Python runtime route failed: {payload}")
        selected = payload.get("selected") or {}
        require(selected.get("valid") is True, f"release app selected runtime is not valid: {payload}")
        require(selected.get("source") == "app-bundled-vmlx-python", f"release app did not select the app-bundled vMLX Python runtime: {payload}")
        require(str(APP / "Contents" / "Resources" / "bundled-python") in selected.get("path", ""), f"release app selected runtime is outside app resources: {payload}")
        require(selected.get("missingModuleCount") == 0, f"release app selected runtime has missing modules: {payload}")
        return str(selected.get("source") or "")
    finally:
        subprocess.run(["pkill", "-x", "ExploitBot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app.poll() is None:
            app.send_signal(signal.SIGTERM)


def build_report(
    *,
    started_at: str,
    finished_at: str,
    manifest: dict,
    app_codesign: str,
    dmg_codesign: str,
    bundled_runtime_source: str,
    has_notary_credentials: bool,
) -> dict:
    notarization_gate = manifest.get("notarizationGate")
    distribution_status = "PASS" if notarization_gate == "passed" else "BLOCKED"
    local_package_status = "PASS"
    return {
        "ok": local_package_status == "PASS",
        "proofType": "release-readiness",
        "proofLevel": "local-package-signature-runtime-and-notarization-gate",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "localPackageStatus": local_package_status,
        "distributionStatus": distribution_status,
        "hasNotaryCredentials": has_notary_credentials,
        "notarizationStatus": manifest.get("notarizationStatus"),
        "notarizationGate": notarization_gate,
        "notarizationGateReason": manifest.get("notarizationGateReason"),
        "artifacts": manifest.get("artifacts") or {},
        "checks": {
            "appCodesign": "PASS" if "valid on disk" in app_codesign else "FAIL",
            "dmgCodesign": "PASS" if "valid on disk" in dmg_codesign else "FAIL",
            "bundledRuntime": "PASS" if bundled_runtime_source == "app-bundled-vmlx-python" else "FAIL",
            "notarization": "PASS" if notarization_gate == "passed" else "BLOCKED",
        },
    }


def write_report(report: dict, output: Path = DEFAULT_OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    started_at = timestamp()
    require(SCRIPT.is_file(), "release package script is missing")
    require(SCRIPT.stat().st_mode & 0o111 != 0, "release package script is not executable")
    require(ENTITLEMENTS.is_file(), "release entitlements are missing")

    has_notary_credentials = bool(
        os.environ.get("EXPLOITBOT_NOTARY_PROFILE")
        or (
            os.environ.get("NOTARIZE_APPLE_ID")
            and os.environ.get("NOTARIZE_TEAM_ID")
            and os.environ.get("NOTARIZE_PASSWORD")
        )
    )
    packaged = run([str(SCRIPT), "--notarize" if has_notary_credentials else "--skip-notarize"])
    require(packaged.returncode == 0, "release package script failed", packaged.stdout)
    require(APP.is_dir(), "signed release app was not created")
    require(DMG.is_file(), "release DMG was not created")
    require(MANIFEST.is_file(), "release manifest was not created")

    info_path = APP / "Contents" / "Info.plist"
    require(info_path.is_file(), "release app Info.plist missing")
    with info_path.open("rb") as handle:
        info = plistlib.load(handle)
    require(info.get("CFBundleIdentifier") == "ai.jangq.ExploitBot", "release bundle identifier mismatch", str(info))
    require((APP / "Contents" / "Resources" / "starter-cves.db").is_file(), "starter CVE database missing from release resources")
    require((APP / "Contents" / "Resources" / "AppIcon.icns").is_file(), "app icon missing from release resources")
    bundled_engine = APP / "Contents" / "Resources" / "ExploitBotEngine"
    require((bundled_engine / "launch.py").is_file(), "bundled engine launch.py missing from release resources")
    require((bundled_engine / "cve_embedder.py").is_file(), "bundled CVE embedder missing from release resources")
    require((bundled_engine / "vmlx_engine" / "server.py").is_file(), "bundled vmlx server missing from release resources")
    require((bundled_engine / "vmlx_engine" / "model_config_registry.py").is_file(), "bundled model config registry missing from release resources")
    require(not (bundled_engine / ".venv").exists(), "release bundle must not include local engine virtualenv")
    require(not (bundled_engine / "testsuite").exists(), "release bundle must not include engine testsuite")
    bundled_python = APP / "Contents" / "Resources" / "bundled-python" / "python"
    bundled_python_bin = bundled_python / "bin" / "python3"
    bundled_python_lib = bundled_python / "lib"
    require(bundled_python_bin.is_file() or bundled_python_bin.is_symlink(), "app-bundled Python runtime missing from release resources")
    require(bundled_python_lib.is_dir(), "app-bundled Python library directory missing from release resources")
    import_check = run_no_bytecode([
        str(bundled_python_bin),
        "-c",
        "import importlib.util, sys; modules=['fastapi','uvicorn','mlx','mlx_lm','transformers','numpy']; missing=[m for m in modules if importlib.util.find_spec(m) is None]; print(sys.version.split()[0]); print(','.join(missing)); raise SystemExit(1 if missing else 0)",
    ])
    require(import_check.returncode == 0, "app-bundled Python runtime cannot import required engine modules", import_check.stdout)

    signed = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    require(signed.returncode == 0, "release app codesign verification failed", signed.stdout)
    details = run(["codesign", "-dvvv", "--entitlements", ":-", str(APP)])
    require("Developer ID Application: ShieldStack LLC" in details.stdout, "release app is not signed with Developer ID", details.stdout)
    require("runtime" in details.stdout, "release app is not signed with hardened runtime", details.stdout)

    dmg_signed = run(["codesign", "--verify", "--verbose=2", str(DMG)])
    require(dmg_signed.returncode == 0, "release DMG codesign verification failed", dmg_signed.stdout)

    bundled_runtime_source = assert_release_app_uses_bundled_runtime()
    signed_after_launch = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    require(signed_after_launch.returncode == 0, "release app codesign verification failed after bundled-runtime launch", signed_after_launch.stdout)

    manifest = json.loads(MANIFEST.read_text())
    require(manifest.get("bundleIdentifier") == "ai.jangq.ExploitBot", "manifest bundle identifier mismatch", str(manifest))
    require(manifest.get("version") == EXPECTED_VERSION, "manifest version mismatch", str(manifest))
    require("Developer ID Application: ShieldStack LLC" in manifest.get("identity", ""), "manifest signing identity mismatch", str(manifest))
    require(manifest.get("teamIdentifier") == "55KGF2S5AY", "manifest team identifier mismatch", str(manifest))
    require(manifest.get("hardenedRuntime") is True, "manifest hardened runtime flag missing", str(manifest))
    if has_notary_credentials:
        require(manifest.get("notarizationStatus") == "submitted-and-stapled", "manifest notarization status mismatch", str(manifest))
        require(manifest.get("notarizationGate") == "passed", "manifest notarization gate mismatch", str(manifest))
        require(
            manifest.get("notarizationGateReason") == "Notarization completed for the app and DMG.",
            "manifest notarization gate reason mismatch",
            str(manifest),
        )
    else:
        require(manifest.get("notarizationStatus") == "not-submitted", "manifest notarization status mismatch", str(manifest))
        require(manifest.get("notarizationGate") == "requires-notary-credentials", "manifest notarization gate mismatch", str(manifest))
        require(
            manifest.get("notarizationGateReason") == "Run with EXPLOITBOT_NOTARY_PROFILE or NOTARIZE_APPLE_ID/NOTARIZE_TEAM_ID/NOTARIZE_PASSWORD.",
            "manifest notarization gate reason mismatch",
            str(manifest),
        )
    require(manifest.get("notaryProfileRequired") is False, "manifest notary profile requirement mismatch", str(manifest))
    artifacts = manifest.get("artifacts", {})
    require(artifacts.get("appPath") == "release/ExploitBot.app", "manifest app path mismatch", str(manifest))
    require(artifacts.get("dmgPath") == "release/ExploitBot.dmg", "manifest DMG path mismatch", str(manifest))
    require(len(artifacts.get("appBinarySha256", "")) == 64, "manifest app binary hash missing", str(manifest))
    require(len(artifacts.get("dmgSha256", "")) == 64, "manifest DMG hash missing", str(manifest))
    resources = manifest.get("resources", {})
    require(resources.get("starterCvesDb") is True, "manifest starter CVE resource flag missing", str(manifest))
    require(resources.get("appIcon") is True, "manifest app icon resource flag missing", str(manifest))
    require(resources.get("pythonEngine") is True, "manifest Python engine resource flag missing", str(manifest))
    require(resources.get("pythonEngineVenv") is False, "manifest must confirm local engine virtualenv is excluded", str(manifest))
    require(resources.get("bundledPythonRuntime") is True, "manifest bundled Python runtime flag missing", str(manifest))
    commands = manifest.get("commands", {})
    require(commands.get("packageUnsigned") == "./script/package_release.sh --skip-notarize", "manifest skip-notarize command mismatch", str(manifest))
    require(commands.get("notarizeWithProfile") == "EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize", "manifest profile notarize command mismatch", str(manifest))
    require(commands.get("notarizeWithEnv") == "source /path/to/.env.signing && ./script/package_release.sh --notarize", "manifest env notarize command mismatch", str(manifest))
    require(commands.get("verifyAppSignature") == "codesign --verify --deep --strict --verbose=2 release/ExploitBot.app", "manifest app signature command mismatch", str(manifest))
    require(commands.get("verifyDmgSignature") == "codesign --verify --verbose=2 release/ExploitBot.dmg", "manifest dmg signature command mismatch", str(manifest))
    require(commands.get("validateStapledApp") == "xcrun stapler validate release/ExploitBot.app", "manifest app stapler command mismatch", str(manifest))
    require(commands.get("validateStapledDmg") == "xcrun stapler validate release/ExploitBot.dmg", "manifest dmg stapler command mismatch", str(manifest))

    write_report(
        build_report(
            started_at=started_at,
            finished_at=timestamp(),
            manifest=manifest,
            app_codesign=signed_after_launch.stdout,
            dmg_codesign=dmg_signed.stdout,
            bundled_runtime_source=bundled_runtime_source,
            has_notary_credentials=has_notary_credentials,
        )
    )
    print("release-readiness proof passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"release-readiness proof failed: {exc}", flush=True)
        raise SystemExit(1)
