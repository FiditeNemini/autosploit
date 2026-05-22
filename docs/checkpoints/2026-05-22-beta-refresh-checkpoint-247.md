# Checkpoint 247 - Coverage Index Gap Contract Summary

## Goal
Carry structured open-gap identity into `/qa/coverage-index` so the top-level QA
map reports the remaining gap contract, not only the gap count.

## Changes
- Updated `scripts/coverage-index-proof.py` to compare
  `/qa/coverage-index.groups.appState.openGapIds` with
  `/qa/gap-ledger.openGapIds`.
- Added `gapContractCount` to `/qa/coverage-index.groups.appState` and checked
  it against `/qa/gap-ledger.gapContracts`.
- Added `openGapIds` to `/qa/coverage-index.groups.appState`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/coverage-index.groups.appState` exposed the
current gap count but not the open gap ID or structured contract count. The
green path makes the aggregate QA index identify `qwenMultimodalRuntime` as the
tracked open gap while preserving the Qwen/MiniMax supported-family boundary.
