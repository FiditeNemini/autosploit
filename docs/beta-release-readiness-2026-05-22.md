# Beta Release Readiness - 2026-05-22

## Artifact

- App bundle: `release/ExploitBot.app`
- DMG: `release/ExploitBot-beta.dmg`
- Packaging script: `script/package_release.sh`
- Readiness proof: `scripts/release-readiness-proof.py`

## Current State

The beta packaging path can now build a SwiftPM release binary, stage a macOS
`.app` bundle, copy bundled resources including `starter-cves.db`, sign the app
with Developer ID and hardened runtime, create a compressed DMG, and sign the
DMG.

Validated identity:

- `Developer ID Application: ShieldStack LLC (55KGF2S5AY)`

Validated local commands:

- `python3 scripts/release-readiness-proof.py`
- `codesign --verify --deep --strict --verbose=2 release/ExploitBot.app`
- `codesign --verify --verbose=2 release/ExploitBot-beta.dmg`
- `spctl -a -vv -t execute release/ExploitBot.app`
- `spctl -a -vv -t open --context context:primary-signature release/ExploitBot-beta.dmg`

## Verification Result

- App signature: valid on disk, satisfies designated requirement.
- DMG signature: valid on disk, satisfies designated requirement.
- App signing authority: Developer ID Application: ShieldStack LLC
  `(55KGF2S5AY)`.
- Hardened runtime: enabled.
- Resource seal: present.
- Gatekeeper status before notarization: rejected as `Unnotarized Developer ID`.

That Gatekeeper result is expected before notarization. The package is ready for
notary submission once a notarytool keychain profile is available.

## Notarization Command

Create or choose a local notarytool keychain profile, then run:

```sh
EXPLOITBOT_NOTARY_PROFILE=<profile-name> ./script/package_release.sh --notarize
```

The script will submit `release/ExploitBot-beta.dmg`, wait for Apple notary
processing, and staple the accepted ticket to the DMG.

## Remaining Release Gate

Before calling this beta distributable complete:

- Run the focused app QA proofs for the current commit.
- Run `python3 scripts/release-readiness-proof.py`.
- Run `./script/package_release.sh --notarize` with a valid notary profile.
- Re-run Gatekeeper assessment against the stapled DMG.
