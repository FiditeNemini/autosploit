# Beta Refresh Checkpoint 435

## Goal

Add an evidence lifecycle flow matrix so every lifecycle stage, storage target,
and handoff has row-level route and proof ownership.

## Changes

- Added `scripts/evidence-lifecycle-flow-matrix-proof.py`.
- Added `/qa/evidence-lifecycle-flow-matrix`.
- Added `/qa/evidence-lifecycle-flow-matrix` to
  `/state.qaCoverage.stateRoutes`.
- Added stage, storage-target, and handoff rows tied to
  `/qa/evidence-lifecycle-coverage`, `/qa/context-flow-matrix`, route owners,
  proof owners, and proof-owner file parity.
- Mirrored `evidenceLifecycleFlowMatrixStageCount`,
  `evidenceLifecycleFlowMatrixStorageTargetCount`,
  `evidenceLifecycleFlowMatrixHandoffCount`,
  `evidenceLifecycleFlowMatrixProofOwnerFileParity`, and
  `evidenceLifecycleFlowMatrixProofFileParity` into
  `/qa/coverage-index.groups.chatAndContext`.
- Updated coverage-index and app matrix proofs to require the new lifecycle
  flow matrix route and mirrors.
- Updated the system review and flow inventory docs with the row-level evidence
  lifecycle contract.

## Proof

- `python3 scripts/evidence-lifecycle-flow-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/evidence-lifecycle-flow-matrix` did not
exist. The green path keeps each evidence lifecycle row tied to route ownership,
proof-owner files, context-flow ownership, docs, and coverage-index mirrors.
