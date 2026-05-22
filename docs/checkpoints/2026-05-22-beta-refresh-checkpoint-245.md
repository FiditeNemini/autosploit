# Checkpoint 245 - Coverage Index Checkpoint Ratio

## Goal
Carry checkpoint documentation completion ratio into `/qa/coverage-index` so the
top-level QA summary reports both checkpoint count and completeness.

## Changes
- Updated `scripts/coverage-index-proof.py` to compare
  `/qa/coverage-index.groups.appState.checkpointCompletionRatio` with
  `/qa/checkpoint-ledger.checkpointCompletionRatio`.
- Added `checkpointCompletionRatio` to `/qa/coverage-index.groups.appState`.
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
checkpoint count but not the completion ratio. The green path makes the top
level QA index carry the same checkpoint documentation health metric as the
checkpoint and audit ledgers.
