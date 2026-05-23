# Beta Refresh Checkpoint 393

## Goal

Classify checkpoint documentation backlog so current checkpoint documentation failures are visible separately from legacy incomplete checkpoint notes.

## Changes

- Added `/qa/checkpoint-ledger` fields for legacy incomplete checkpoint cutoff/count/list, current incomplete checkpoint count/list, and the current checkpoint docs complete flag.
- Mirrored those fields through `/qa/audit-ledger` and the `/qa/coverage-index.groups.appState` aggregate.
- Extended checkpoint, audit, coverage-index, and app QA matrix proofs so all three API surfaces stay in sync.
- Updated the system review and flow inventory docs with the new legacy/current checkpoint backlog semantics.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red checkpoint proof first failed because incomplete checkpoint docs were only reported as one combined list. The red audit and coverage proofs then failed until the new fields were mirrored through the rollup surfaces.
