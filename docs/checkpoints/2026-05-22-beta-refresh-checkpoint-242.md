# Checkpoint 242 - Numeric Checkpoint Ledger Lists

## Goal

Keep all checkpoint-ledger path lists in numeric checkpoint order so clients do
not see checkpoint 90 after checkpoint 241.

## Changes

- Updated `scripts/checkpoint-ledger-proof.py` to expect numeric checkpoint
  ordering.
- Updated `GET /qa/checkpoint-ledger` so `checkpoints`,
  `incompleteCheckpoints`, and complete checkpoint accounting are derived from
  numerically ordered checkpoint URLs.
- Kept `latestCheckpoint` and `latestCheckpointNumber` based on the same
  numeric order.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/checkpoint-ledger.checkpoints` still used
lexicographic filename order. The green path makes the checkpoint ledger
internally consistent with the numeric latest-checkpoint contract.
