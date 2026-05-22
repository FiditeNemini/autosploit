# Checkpoint 348 - Audit Checkpoint Frontier Mirrors

## Goal

Make `/qa/coverage-index.groups.appState` preserve the audit ledger checkpoint
completion ratio and latest checkpoint frontier.

## Changes

- Added `auditCheckpointCompletionRatio` to the coverage-index app-state
  aggregate.
- Added `auditLatestCheckpoint` and `auditLatestCheckpointNumber` to the
  coverage-index app-state aggregate.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/coverage-index.groups.appState` mirrored audit
checkpoint counts and path lists but not the audit checkpoint completion ratio
or latest checkpoint frontier. The green path keeps the audit checkpoint
frontier directly auditable from the top-level QA index.
