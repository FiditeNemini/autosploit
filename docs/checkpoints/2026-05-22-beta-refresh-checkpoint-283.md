# Checkpoint 283 - App Matrix Tool Flow Status Contract

## Goal
Lift the visible tool-flow tab activity status contract into the broad app QA matrix.

## Changes
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require `tabActivityStatuses`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require `tabActivityStatusCount` and `tabActivityStatusParity`.
- Updated `scripts/app-qa-matrix-smoke-proof.py` to require `tabActivityIndicatorContract`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/tool-flow-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
This is a verification-hardening slice: `/qa/tool-flow-coverage` already exposed the visible tab activity status contract, and the broad smoke gate now checks those same fields.
