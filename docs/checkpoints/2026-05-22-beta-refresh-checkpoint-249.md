# Checkpoint 249 - Coverage Index Checkpoint Count Breakdown

## Goal
Carry complete and incomplete checkpoint counts into `/qa/coverage-index` so
the top-level QA map explains the checkpoint completion ratio without requiring
a second checkpoint-ledger request.

## Changes
- Updated `scripts/coverage-index-proof.py` to compare
  `/qa/coverage-index.groups.appState.completeCheckpointCount` with
  `/qa/checkpoint-ledger.completeCheckpointCount`.
- Added `incompleteCheckpointCount` to `/qa/coverage-index.groups.appState` and
  checked it against `/qa/checkpoint-ledger.incompleteCheckpoints`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/coverage-index.groups.appState` exposed total
checkpoint count and completion ratio but not the complete/incomplete count
breakdown. The green path makes one aggregate QA response show checkpoint
total, complete count, incomplete count, completion ratio, latest checkpoint,
and the current open gap summary.
