# Checkpoint 235 - QA Matrix Ledger Cross-Checks

## Goal

Make the broad app QA matrix exercise the proof, artifact, checkpoint, and audit
ledger endpoints directly instead of relying only on `/qa/coverage-index`.

## Changes

- Updated `scripts/app-qa-matrix-smoke-proof.py` to fetch:
  - `/qa/proof-ledger`
  - `/qa/artifact-ledger`
  - `/qa/checkpoint-ledger`
  - `/qa/audit-ledger`
- Added route-contract assertions for those ledgers through
  `/state.qaCoverage.stateRoutes`.
- Added coverage-index app-state group assertions for proof ledger count,
  checkpoint ledger count, and audit ledger total.
- Added direct cross-checks that `/qa/audit-ledger` matches the proof,
  artifact, and checkpoint ledgers.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The stricter app QA matrix passed immediately because the app already exposed
the ledger routes from the previous checkpoints. This checkpoint records the
broader regression guard so the single smoke proof now covers the global ledger
surface directly.
