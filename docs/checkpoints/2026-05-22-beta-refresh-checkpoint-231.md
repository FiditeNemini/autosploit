# Checkpoint 231 - Global Artifact Ledger

## Goal

Expose a machine-readable ledger of checked-in proof artifacts so visual
screenshots and live proof JSONs can be audited through the app QA API.

## Changes

- Added `scripts/artifact-ledger-proof.py`.
- Added `GET /qa/artifact-ledger`, dynamically discovering visual manifests,
  screenshot capture counts, and live proof JSON files.
- Added live proof status accounting with support for both `ok=true` and
  `status=passed` schemas, plus failed live proof paths.
- Added `/qa/artifact-ledger` to `/state.qaCoverage.stateRoutes`.
- Added the artifact-ledger route and artifact counts to
  `/qa/coverage-index.groups.appState`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof first failed because `/qa/artifact-ledger` did not exist. After
the route was added, the proof exposed mixed historical live artifact schemas:
some use `ok=true`, context-window artifacts use `status=passed`, and some older
diagnostic runs are explicit failures. The green path preserves those statuses
instead of flattening every live JSON into a false success claim.
