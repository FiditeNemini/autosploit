#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/release-manifest.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-04-notarization-preflight.json"
ENV_CREDENTIAL_NAMES = ["NOTARIZE_APPLE_ID", "NOTARIZE_TEAM_ID", "NOTARIZE_PASSWORD"]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def credential_state(env: dict[str, str] | None = None) -> dict[str, Any]:
    source = os.environ if env is None else env
    profile_configured = bool(source.get("EXPLOITBOT_NOTARY_PROFILE"))
    present_env_inputs = [name for name in ENV_CREDENTIAL_NAMES if bool(source.get(name))]
    missing_env_inputs = [name for name in ENV_CREDENTIAL_NAMES if not source.get(name)]
    env_credentials_configured = len(present_env_inputs) == len(ENV_CREDENTIAL_NAMES)
    if profile_configured:
        mode = "keychain-profile"
        validation_status = "input-present-not-live-validated"
    elif env_credentials_configured:
        mode = "apple-id-team-password"
        validation_status = "input-present-not-live-validated"
    else:
        mode = "not-configured"
        validation_status = "missing-credential-input"
    return {
        "profileConfigured": profile_configured,
        "envCredentialsConfigured": env_credentials_configured,
        "configuredInputs": (
            (["EXPLOITBOT_NOTARY_PROFILE"] if profile_configured else [])
            + present_env_inputs
        ),
        "missingEnvInputs": missing_env_inputs,
        "acceptedCredentialModes": [
            "EXPLOITBOT_NOTARY_PROFILE",
            "NOTARIZE_APPLE_ID+NOTARIZE_TEAM_ID+NOTARIZE_PASSWORD",
        ],
        "selectedCredentialMode": mode,
        "credentialValidationStatus": validation_status,
        "credentialLiveValidation": "NOT_RUN",
        "credentialLiveValidationReason": (
            "Preflight checks local input presence and stapled-ticket state only; "
            "run ./script/package_release.sh --notarize to submit to Apple and staple artifacts."
        ),
        "profileNameRedacted": profile_configured,
        "envCredentialValuesRedacted": bool(present_env_inputs),
    }


def stapler_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(ROOT)),
            "status": "MISSING_ARTIFACT",
            "returnCode": None,
            "output": "",
        }
    result = run(["xcrun", "stapler", "validate", str(path)])
    output = result.stdout.strip()
    if result.returncode == 0:
        status = "STAPLED_TICKET_PRESENT"
    elif "does not have a ticket stapled" in output:
        status = "NO_STAPLED_TICKET"
    else:
        status = "VALIDATION_FAILED"
    return {
        "path": str(path.relative_to(ROOT)),
        "status": status,
        "returnCode": result.returncode,
        "output": output,
    }


def codesign_verify_status(path: Path, *, deep: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(ROOT)),
            "status": "MISSING_ARTIFACT",
            "returnCode": None,
            "output": "",
        }
    cmd = ["codesign", "--verify"]
    if deep:
        cmd += ["--deep", "--strict"]
    cmd += ["--verbose=4", str(path)]
    result = run(cmd)
    return {
        "path": str(path.relative_to(ROOT)),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "returnCode": result.returncode,
        "output": result.stdout.strip()[-4000:],
    }


def codesign_details(path: Path) -> dict[str, Any]:
    result = run(["codesign", "-dv", "--verbose=4", str(path)])
    output = result.stdout
    authorities = [
        line.split("=", 1)[1]
        for line in output.splitlines()
        if line.startswith("Authority=")
    ]
    flags_line = next((line for line in output.splitlines() if line.startswith("CodeDirectory ")), "")
    identifier = next((line.split("=", 1)[1] for line in output.splitlines() if line.startswith("Identifier=")), None)
    team_identifier = next((line.split("=", 1)[1] for line in output.splitlines() if line.startswith("TeamIdentifier=")), None)
    timestamp = next((line.split("=", 1)[1] for line in output.splitlines() if line.startswith("Timestamp=")), None)
    return {
        "path": str(path.relative_to(ROOT)),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "identifier": identifier,
        "teamIdentifier": team_identifier,
        "timestamp": timestamp,
        "hardenedRuntime": "(runtime)" in flags_line,
        "authorities": authorities,
        "rawSummary": output.strip()[-4000:],
    }


def entitlements_status(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["codesign", "-d", "--entitlements", ":-", str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    raw = result.stdout
    try:
        converted = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", "-"],
            cwd=ROOT,
            text=True,
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        entitlements = json.loads(converted.stdout) if converted.returncode == 0 and converted.stdout.strip() else {}
    except Exception:
        entitlements = {}
    return {
        "path": str(path.relative_to(ROOT)),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "entitlements": entitlements,
        "hasHardenedRuntimeUnsafeEntitlements": any(
            key.startswith("com.apple.security.cs.")
            for key in entitlements
        ),
        "rawSummary": (raw + result.stderr).strip()[-4000:],
    }


def gatekeeper_assessment(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(ROOT)),
            "status": "MISSING_ARTIFACT",
            "returnCode": None,
            "output": "",
        }
    result = run(["spctl", "-a", "-vvv", "-t", "open", str(path)])
    output = result.stdout.strip()
    if result.returncode == 0:
        status = "PASS"
    elif "rejected" in output:
        status = "REJECTED"
    else:
        status = "FAIL"
    return {
        "path": str(path.relative_to(ROOT)),
        "status": status,
        "returnCode": result.returncode,
        "output": output[-4000:],
    }


def known_keychain_profile_probe(profile_name: str = "EXPLOITBOT_NOTARY_PROFILE") -> dict[str, Any]:
    result = run(["security", "find-generic-password", "-s", profile_name])
    return {
        "profileNameRedacted": bool(profile_name),
        "profileNameProbe": profile_name,
        "status": "FOUND" if result.returncode == 0 else "NOT_FOUND",
        "returnCode": result.returncode,
    }


def build_report(
    *,
    notarytool_available: bool,
    credentials: dict[str, Any],
    stapler: dict[str, Any],
    manifest: dict[str, Any],
    artifacts: dict[str, str],
    signing: dict[str, Any] | None = None,
    gatekeeper: dict[str, Any] | None = None,
    keychainProfiles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    has_credentials = bool(
        credentials.get("profileConfigured") or credentials.get("envCredentialsConfigured")
    )
    app_stapled = (stapler.get("app") or {}).get("status") == "STAPLED_TICKET_PRESENT"
    dmg_stapled = (stapler.get("dmg") or {}).get("status") == "STAPLED_TICKET_PRESENT"
    manifest_passed = manifest.get("notarizationGate") == "passed"
    distribution_ready = manifest_passed and app_stapled and dmg_stapled

    if not notarytool_available:
        next_action = "install-xcode-notarytool"
    elif not has_credentials:
        next_action = "configure-notary-credentials-and-run-package-notarize"
    elif not distribution_ready:
        next_action = "run-package-release-notarize-and-staple"
    else:
        next_action = "distribution-ready"

    return {
        "ok": notarytool_available,
        "proofType": "notarization-preflight",
        "proofLevel": "local-notarytool-credential-input-and-stapled-ticket-gate",
        "distributionStatus": "PASS" if distribution_ready else "BLOCKED",
        "notarizationStatus": manifest.get("notarizationStatus"),
        "notarizationGate": manifest.get("notarizationGate"),
        "notarizationGateReason": manifest.get("notarizationGateReason"),
        "nextAction": next_action,
        "secretsRedacted": True,
        "credentials": credentials,
        "credentialSetup": {
            "profileCommand": (
                "xcrun notarytool store-credentials <profile-name> "
                "--apple-id <apple-id> --team-id <team-id> --password <app-specific-password>"
            ),
            "envCommand": (
                "export NOTARIZE_APPLE_ID=<apple-id> "
                "NOTARIZE_TEAM_ID=<team-id> "
                "NOTARIZE_PASSWORD=<app-specific-password>"
            ),
            "notarizeWithProfile": (
                "EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize"
            ),
            "notarizeWithEnv": "source /path/to/.env.signing && ./script/package_release.sh --notarize",
            "postNotarizeVerification": [
                "xcrun stapler validate release/ExploitBot.app",
                "xcrun stapler validate release/ExploitBot.dmg",
                "python3 scripts/notarization-preflight-proof.py",
                "python3 scripts/release-readiness-proof.py",
                "python3 scripts/goal-requirement-audit-proof.py",
            ],
        },
        "artifacts": artifacts,
        "signing": signing or {},
        "gatekeeper": gatekeeper or {},
        "keychainProfiles": keychainProfiles or {},
        "stapler": stapler,
        "checks": {
            "notarytool": "PASS" if notarytool_available else "FAIL",
            "notaryCredentials": "PASS" if has_credentials else "BLOCKED",
            "credentialLiveValidation": "NOT_RUN",
            "developerIDSignature": (
                "PASS"
                if (signing or {}).get("appVerify", {}).get("status") == "PASS"
                and (signing or {}).get("dmgVerify", {}).get("status") == "PASS"
                else "FAIL"
            ),
            "hardenedRuntime": "PASS" if (signing or {}).get("appDetails", {}).get("hardenedRuntime") is True else "FAIL",
            "gatekeeperAssessment": "PASS" if (gatekeeper or {}).get("app", {}).get("status") == "PASS" else "BLOCKED",
            "manifestGate": "PASS" if manifest_passed else "BLOCKED",
            "appStapledTicket": "PASS" if app_stapled else "BLOCKED",
            "dmgStapledTicket": "PASS" if dmg_stapled else "BLOCKED",
        },
    }


def main() -> None:
    started_at = timestamp()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_artifacts = manifest.get("artifacts") or {}
    app_path = ROOT / str(manifest_artifacts.get("appPath", "release/ExploitBot.app"))
    dmg_path = ROOT / str(manifest_artifacts.get("dmgPath", "release/ExploitBot.dmg"))
    notarytool = run(["xcrun", "notarytool", "--help"])
    report = build_report(
        notarytool_available=notarytool.returncode == 0,
        credentials=credential_state(),
        stapler={
            "app": stapler_status(app_path),
            "dmg": stapler_status(dmg_path),
        },
        manifest=manifest,
        artifacts={
            "appPath": str(app_path.relative_to(ROOT)),
            "dmgPath": str(dmg_path.relative_to(ROOT)),
        },
        signing={
            "appVerify": codesign_verify_status(app_path, deep=True),
            "dmgVerify": codesign_verify_status(dmg_path),
            "appDetails": codesign_details(app_path),
            "appEntitlements": entitlements_status(app_path),
        },
        gatekeeper={
            "app": gatekeeper_assessment(app_path),
        },
        keychainProfiles={
            "defaultProfileProbe": known_keychain_profile_probe(),
        },
    )
    report["startedAt"] = started_at
    report["finishedAt"] = timestamp()
    report["generatedAt"] = report["finishedAt"]
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"notarization preflight proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
