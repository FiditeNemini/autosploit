#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "release-manifest.json"
DEFAULT_OUTPUT = ROOT / "docs/live-proofs/2026-07-05-release-public-truth.json"


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        suffix = "" if detail is None else "\n" + json.dumps(detail, indent=2, sort_keys=True)[:4000]
        raise AssertionError(message + suffix)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)


def run_json(cmd: list[str]) -> dict[str, Any] | list[Any]:
    result = run(cmd)
    require(result.returncode == 0, f"command failed: {' '.join(cmd)}", result.stdout)
    return json.loads(result.stdout)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_digest(value: Any) -> str:
    text = str(value or "")
    if text.startswith("sha256:"):
        return text.split(":", 1)[1]
    return text


def find_asset(release: dict[str, Any], name: str) -> dict[str, Any] | None:
    for asset in release.get("assets") or []:
        if asset.get("name") == name:
            return asset
    return None


def status_from_bool(value: bool, fail_status: str = "BLOCKED") -> str:
    return "PASS" if value else fail_status


def build_report(
    *,
    started_at: str,
    finished_at: str,
    repo: dict[str, Any],
    current_head: str,
    branch: str,
    manifest: dict[str, Any],
    local_manifest_sha256: str,
    releases: list[dict[str, Any]],
) -> dict[str, Any]:
    version = str(manifest.get("version") or "")
    expected_tag = version if version.startswith("v") else f"v{version}"
    published = next((release for release in releases if release.get("tagName") == expected_tag), None)
    artifacts = manifest.get("artifacts") or {}
    local_dmg_sha256 = str(artifacts.get("dmgSha256") or "")
    notarization_gate = manifest.get("notarizationGate")

    dmg_asset = find_asset(published or {}, "ExploitBot-beta.dmg")
    manifest_asset = find_asset(published or {}, "release-manifest.json")
    published_dmg_sha256 = normalize_digest((dmg_asset or {}).get("digest"))
    published_manifest_sha256 = normalize_digest((manifest_asset or {}).get("digest"))

    repo_public = repo.get("visibility") == "PUBLIC"
    matching_release_found = published is not None and published.get("isDraft") is False
    published_dmg_ready = bool(dmg_asset and dmg_asset.get("state") == "uploaded" and published_dmg_sha256)
    published_manifest_ready = bool(manifest_asset and manifest_asset.get("state") == "uploaded" and published_manifest_sha256)
    dmg_matches = published_dmg_ready and published_dmg_sha256 == local_dmg_sha256
    manifest_matches = published_manifest_ready and published_manifest_sha256 == local_manifest_sha256
    source_matches = bool(published and published.get("targetCommitish") == current_head)
    notarization_passed = notarization_gate == "passed"
    release_claim_allowed = all([
        repo_public,
        matching_release_found,
        published_dmg_ready,
        published_manifest_ready,
        dmg_matches,
        manifest_matches,
        source_matches,
        notarization_passed,
    ])
    public_release_status = "PASS" if release_claim_allowed else ("PARTIAL" if matching_release_found else "BLOCKED")

    return {
        "ok": True,
        "proofType": "release-public-truth",
        "proofLevel": "github-public-release-metadata-local-manifest-hash-and-notary-boundary",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "generatedAt": finished_at,
        "repository": {
            "nameWithOwner": repo.get("nameWithOwner"),
            "url": repo.get("url"),
            "visibility": repo.get("visibility"),
        },
        "branch": branch,
        "currentHead": current_head,
        "expectedReleaseTag": expected_tag,
        "localPackageStatus": "PASS" if local_dmg_sha256 and local_manifest_sha256 else "BLOCKED",
        "publicReleaseStatus": public_release_status,
        "distributionStatus": "PASS" if release_claim_allowed else "BLOCKED",
        "releaseClaimAllowed": release_claim_allowed,
        "notarizationGate": notarization_gate,
        "notarizationStatus": manifest.get("notarizationStatus"),
        "localArtifacts": {
            "dmgPath": artifacts.get("dmgPath"),
            "dmgSha256": local_dmg_sha256,
            "manifestPath": str(MANIFEST.relative_to(ROOT)),
            "manifestSha256": local_manifest_sha256,
        },
        "publishedRelease": {
            "name": (published or {}).get("name"),
            "tagName": (published or {}).get("tagName"),
            "url": (published or {}).get("url"),
            "isDraft": (published or {}).get("isDraft"),
            "isPrerelease": (published or {}).get("isPrerelease"),
            "publishedAt": (published or {}).get("publishedAt"),
            "targetCommitish": (published or {}).get("targetCommitish"),
            "dmgAsset": {
                "name": (dmg_asset or {}).get("name"),
                "digest": (dmg_asset or {}).get("digest"),
                "state": (dmg_asset or {}).get("state"),
                "size": (dmg_asset or {}).get("size"),
                "url": (dmg_asset or {}).get("url"),
            },
            "manifestAsset": {
                "name": (manifest_asset or {}).get("name"),
                "digest": (manifest_asset or {}).get("digest"),
                "state": (manifest_asset or {}).get("state"),
                "size": (manifest_asset or {}).get("size"),
                "url": (manifest_asset or {}).get("url"),
            },
        },
        "checks": {
            "repoPublic": status_from_bool(repo_public),
            "matchingReleaseFound": status_from_bool(matching_release_found),
            "publishedDmgAsset": status_from_bool(published_dmg_ready),
            "publishedManifestAsset": status_from_bool(published_manifest_ready),
            "localDmgMatchesPublished": status_from_bool(dmg_matches),
            "localManifestMatchesPublished": status_from_bool(manifest_matches),
            "sourceRevisionMatchesPublished": status_from_bool(source_matches),
            "notarizationGate": status_from_bool(notarization_passed),
        },
        "nextAction": "none" if release_claim_allowed else "notarize-staple-and-publish-current-release-assets",
        "secretsRead": False,
        "assetDownloadPerformed": False,
    }


def write_report(report: dict[str, Any], output: Path = DEFAULT_OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    started_at = timestamp()
    require(MANIFEST.is_file(), "release manifest is missing", str(MANIFEST))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts") or {}
    dmg_path = ROOT / str(artifacts.get("dmgPath") or "")
    require(dmg_path.is_file(), "release DMG named by manifest is missing", artifacts)
    actual_dmg_sha256 = sha256_file(dmg_path)
    require(actual_dmg_sha256 == artifacts.get("dmgSha256"), "local DMG hash does not match release manifest", {
        "actual": actual_dmg_sha256,
        "manifest": artifacts.get("dmgSha256"),
    })

    repo = run_json(["gh", "repo", "view", "--json", "nameWithOwner,visibility,url"])
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    branch = run(["git", "branch", "--show-current"]).stdout.strip()
    version = str(manifest.get("version") or "")
    expected_tag = version if version.startswith("v") else f"v{version}"
    release = run_json([
        "gh",
        "release",
        "view",
        expected_tag,
        "--json",
        "name,tagName,isPrerelease,isDraft,url,assets,targetCommitish,publishedAt,createdAt",
    ])
    finished_at = timestamp()
    report = build_report(
        started_at=started_at,
        finished_at=finished_at,
        repo=repo,
        current_head=head,
        branch=branch,
        manifest=manifest,
        local_manifest_sha256=sha256_file(MANIFEST),
        releases=[release],
    )
    write_report(report)
    print(f"release public truth proof wrote {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"release public truth proof failed: {exc}", flush=True)
        raise SystemExit(1)
