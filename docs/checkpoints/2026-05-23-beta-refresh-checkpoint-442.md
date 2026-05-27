# Beta Refresh Checkpoint 442

## Goal

Add a subtab lifecycle matrix so every valid tab subtab has row-level subtab,
proof, tab-flow, session-workflow, and visual-surface ownership.

## Changes

- Added `scripts/subtab-lifecycle-matrix-proof.py`.
- Added `/qa/subtab-lifecycle-matrix`.
- Added `/qa/subtab-lifecycle-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per `/qa/subtab-coverage` valid subtab with tab, subtab,
  default/active status, proof owner, `/qa/subtab-coverage`,
  `/qa/tab-tool-function-flow`, `/qa/session-workflow-matrix`, and
  `/qa/visual-surface-matrix` linkage.
- Mirrored `subtabLifecycleMatrixCount`,
  `subtabLifecycleMatrixProofOwnerFileParity`,
  `subtabLifecycleMatrixProofFileParity`, and
  `subtabLifecycleMatrixTabToolFunctionFlowCount` into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Updated coverage-index and app matrix proofs to require the new subtab
  lifecycle matrix route and mirrors.
- Updated the system review and flow inventory docs with the subtab lifecycle
  matrix contract.

## Proof

- `python3 scripts/subtab-lifecycle-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/subtab-lifecycle-matrix` did not exist. The
green path keeps every valid subtab tied to source subtab coverage,
proof-owner files, tab/tool/function flow, session workflow coverage, visual
surface coverage, docs, and coverage-index mirrors.
