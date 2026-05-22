# Checkpoint 325 - Visual Capture Evidence Aggregate

## Goal

Make the top-level coverage index preserve visual capture status and missing
capture details from `/qa/artifact-ledger`.

## Changes

- Added `artifactLedgerVisualCaptureStatus` to
  `/qa/coverage-index.groups.appState`.
- Added `missingVisualCaptures` to the same aggregate group.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/artifact-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The red coverage-index proof failed because the app-state aggregate exposed
visual manifest paths, live proof paths/status, and missing visual capture
count, but not the per-capture status map or missing capture list. The green
path keeps screenshot capture existence evidence traceable from the top-level
QA index.
