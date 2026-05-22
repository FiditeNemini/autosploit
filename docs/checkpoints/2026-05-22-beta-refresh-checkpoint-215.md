# Checkpoint 215 - Settings Visual Manifest Coverage

## Goal

Make `/qa/settings-coverage` expose the checked-in visual proof manifests that
back Settings category, model/cache, live-cache, CVE, tool, and log UI claims.

## Changes

- Strengthened `scripts/settings-coverage-proof.py` to require Settings visual
  manifest paths and verify each manifest has capture artifacts on disk.
- Updated `GET /qa/settings-coverage` with `visualManifests` and
  `visualManifestCount`.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level smoke
  proof catches missing Settings visual manifest accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/visual-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/settings-coverage` named visual proof scripts
but did not expose the concrete visual manifest paths. The green path makes the
Settings aggregate auditable the same way the Chat aggregate is.
