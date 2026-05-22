# Checkpoint 324 - Artifact Evidence Aggregate

## Goal

Make the top-level coverage index preserve artifact ledger evidence paths and
live proof status from `/qa/artifact-ledger`.

## Changes

- Added `artifactLedgerVisualManifests` to
  `/qa/coverage-index.groups.appState`.
- Added `artifactLedgerLiveProofs` and `artifactLedgerLiveProofStatus` to the
  same aggregate group.
- Extended `scripts/coverage-index-proof.py` to compare those aggregate fields
  against `/qa/artifact-ledger`.
- Extended `scripts/app-qa-matrix-smoke-proof.py` with the same broad smoke
  checks.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`

## Notes

The first red run exposed a proof-script variable error, which was corrected.
The corrected red proof then failed because the app-state aggregate exposed
artifact manifest/live proof counts and missing visual capture count, but not
the manifest paths, live proof paths, or live proof pass/fail status. The green
path keeps screenshot manifests and live JSON evidence traceable from the
top-level QA index.
