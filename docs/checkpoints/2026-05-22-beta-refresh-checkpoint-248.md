# Checkpoint 248 - Coverage Index Latest Checkpoint

## Goal
Carry the latest checkpoint path and numeric checkpoint ID into
`/qa/coverage-index` so the top-level QA map identifies the current
documentation frontier.

## Changes
- Updated `scripts/coverage-index-proof.py` to compare
  `/qa/coverage-index.groups.appState.latestCheckpoint` and
  `latestCheckpointNumber` with `/qa/checkpoint-ledger`.
- Added `latestCheckpoint` and `latestCheckpointNumber` to
  `/qa/coverage-index.groups.appState`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/coverage-index.groups.appState` exposed
checkpoint count and completion ratio but not the current checkpoint identity.
The green path lets one aggregate QA request report the latest checkpoint path,
number, completion health, and open-gap summary together.
