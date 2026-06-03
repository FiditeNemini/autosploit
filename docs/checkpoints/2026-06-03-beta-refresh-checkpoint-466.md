# Beta Refresh Checkpoint 466 - Local Beta DMG Rebuild

Date: 2026-06-03

## Goal

End the session with a fresh local beta package build and a clean tracked handoff
without committing ignored release artifacts or private signing/notary material.

## Changes

- Rebuilt the ignored local beta package artifacts in `release/`.
- Added the fresh local non-notarized DMG SHA256 to `README.md` without
  changing the published notarized release SHA.
- Added this checkpoint to keep the local package evidence tracked while leaving
  signing/notary secrets and generated release artifacts out of git.

## Build

- `swift build --package-path ExploitBot -c debug`
- `./script/package_release.sh --skip-notarize`

The package script rebuilt `release/ExploitBot.app`, bundled the vMLX-compatible
Python runtime and ExploitBot engine resources, signed nested native code, signed
the app with hardened runtime, created `release/ExploitBot-beta.dmg`, signed the
DMG, and wrote `release/release-manifest.json`.

## Proof

- `codesign --verify --deep --strict --verbose=2 release/ExploitBot.app`
- `codesign --verify --verbose=2 release/ExploitBot-beta.dmg`
- `hdiutil verify release/ExploitBot-beta.dmg`
- `python3 -m json.tool release/release-manifest.json`
- `git diff --check`
- Private-info sweep for the site SSH host, password text, and deployment path.

Fresh local DMG SHA256:

```text
adec88db78ba8eda813ea16adf8d59d3016380a68442f810a7411aa74b3bf483
```

Manifest highlights:

- `version`: `0.1.0-beta`
- `teamIdentifier`: `55KGF2S5AY`
- `hardenedRuntime`: `true`
- `notarizationStatus`: `not-submitted`
- `notarizationGate`: `requires-notary-credentials`
- `pythonEngine`: `true`
- `bundledPythonRuntime`: `true`
- `starterCvesDb`: `true`
- `pythonEngineVenv`: `false`

## Remaining

This checkpoint proves a fresh signed local package and valid DMG image. It does
not notarize or upload the new DMG, and it does not close the known Qwen
multimodal runtime promotion gap.
