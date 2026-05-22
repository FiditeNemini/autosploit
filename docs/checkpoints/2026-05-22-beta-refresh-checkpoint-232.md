# Checkpoint 232 - Artifact Capture Status

## Goal

Make screenshot artifact existence machine-visible through the app QA API and
top-level coverage index.

## Changes

- Strengthened `scripts/artifact-ledger-proof.py` to require
  `visualCaptureStatus` and an empty `missingVisualCaptures` list.
- Updated `GET /qa/artifact-ledger` to report per-capture existence and missing
  screenshot paths.
- Strengthened `scripts/coverage-index-proof.py` to require
  `missingVisualCaptureCount == 0`.
- Updated `/qa/coverage-index.groups.appState` with `missingVisualCaptureCount`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red artifact proof failed because `/qa/artifact-ledger` exposed visual
counts but not per-capture status. The red coverage-index proof then failed
until missing visual capture count was rolled up to the app-state group.
