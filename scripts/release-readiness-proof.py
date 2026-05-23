#!/usr/bin/env python3
from __future__ import annotations

import plistlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script" / "package_release.sh"
APP = ROOT / "release" / "ExploitBot.app"
DMG = ROOT / "release" / "ExploitBot-beta.dmg"
MANIFEST = ROOT / "release" / "release-manifest.json"
ENTITLEMENTS = ROOT / "ExploitBot" / "ExploitBot.entitlements"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def require(condition: bool, message: str, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{message}\n{detail}".strip())


def main() -> None:
    require(SCRIPT.is_file(), "release package script is missing")
    require(SCRIPT.stat().st_mode & 0o111 != 0, "release package script is not executable")
    require(ENTITLEMENTS.is_file(), "release entitlements are missing")

    packaged = run([str(SCRIPT), "--skip-notarize"])
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

    signed = run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    require(signed.returncode == 0, "release app codesign verification failed", signed.stdout)
    details = run(["codesign", "-dvvv", "--entitlements", ":-", str(APP)])
    require("Developer ID Application: ShieldStack LLC" in details.stdout, "release app is not signed with Developer ID", details.stdout)
    require("runtime" in details.stdout, "release app is not signed with hardened runtime", details.stdout)

    dmg_signed = run(["codesign", "--verify", "--verbose=2", str(DMG)])
    require(dmg_signed.returncode == 0, "release DMG codesign verification failed", dmg_signed.stdout)

    manifest = json.loads(MANIFEST.read_text())
    require(manifest.get("bundleIdentifier") == "ai.jangq.ExploitBot", "manifest bundle identifier mismatch", str(manifest))
    require(manifest.get("version") == "0.1.0-beta", "manifest version mismatch", str(manifest))
    require("Developer ID Application: ShieldStack LLC" in manifest.get("identity", ""), "manifest signing identity mismatch", str(manifest))
    require(manifest.get("teamIdentifier") == "55KGF2S5AY", "manifest team identifier mismatch", str(manifest))
    require(manifest.get("hardenedRuntime") is True, "manifest hardened runtime flag missing", str(manifest))
    require(manifest.get("notarizationStatus") == "not-submitted", "manifest notarization status mismatch", str(manifest))
    require(manifest.get("notarizationGate") == "requires-notary-profile", "manifest notarization gate mismatch", str(manifest))
    require(manifest.get("notaryProfileRequired") is True, "manifest notary profile requirement missing", str(manifest))
    require(
        manifest.get("notarizationGateReason") == "Notarization is intentionally skipped until EXPLOITBOT_NOTARY_PROFILE names a local notarytool keychain profile.",
        "manifest notarization gate reason mismatch",
        str(manifest),
    )
    artifacts = manifest.get("artifacts", {})
    require(artifacts.get("appPath") == "release/ExploitBot.app", "manifest app path mismatch", str(manifest))
    require(artifacts.get("dmgPath") == "release/ExploitBot-beta.dmg", "manifest DMG path mismatch", str(manifest))
    require(len(artifacts.get("appBinarySha256", "")) == 64, "manifest app binary hash missing", str(manifest))
    require(len(artifacts.get("dmgSha256", "")) == 64, "manifest DMG hash missing", str(manifest))
    resources = manifest.get("resources", {})
    require(resources.get("starterCvesDb") is True, "manifest starter CVE resource flag missing", str(manifest))
    require(resources.get("appIcon") is True, "manifest app icon resource flag missing", str(manifest))
    commands = manifest.get("commands", {})
    require(commands.get("packageUnsigned") == "./script/package_release.sh --skip-notarize", "manifest skip-notarize command mismatch", str(manifest))
    require(commands.get("notarize") == "EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize", "manifest notarize command mismatch", str(manifest))
    require(commands.get("verifyAppSignature") == "codesign --verify --deep --strict --verbose=2 release/ExploitBot.app", "manifest app signature command mismatch", str(manifest))
    require(commands.get("verifyDmgSignature") == "codesign --verify --verbose=2 release/ExploitBot-beta.dmg", "manifest dmg signature command mismatch", str(manifest))

    print("release-readiness proof passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"release-readiness proof failed: {exc}", flush=True)
        raise SystemExit(1)
