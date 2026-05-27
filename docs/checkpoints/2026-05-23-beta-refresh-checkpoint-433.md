# Beta Refresh Checkpoint 433

## Goal

Add an individual function proof matrix so every Swift function parsed by the
function-flow inventory is tied to an owning QA route and existing proof owner.

## Changes

- Added `scripts/function-proof-matrix-proof.py`.
- Added `/qa/function-proof-matrix`.
- Added `/qa/function-proof-matrix` to `/state.qaCoverage.stateRoutes`.
- Added a function proof matrix snapshot that consumes
  `/qa/function-flow-inventory`, keeps one row per function, maps each function
  group to its owning QA route, and verifies proof-owner file existence.
- Mirrored `functionProofMatrixCount`, `functionProofMatrixRowParity`,
  `functionProofMatrixGroupRouteParity`,
  `functionProofMatrixProofOwnerFileParity`, and
  `functionProofMatrixProofFileParity` into
  `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the new individual
  function proof matrix route and mirror.
- Updated the system review and flow inventory docs with the function proof
  matrix contract.

## Proof

- `python3 scripts/function-proof-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/function-proof-matrix` did not exist. The
green path keeps individual Swift function rows tied to proof-owner files,
owning routes, state route coverage, docs, and coverage-index parity.
