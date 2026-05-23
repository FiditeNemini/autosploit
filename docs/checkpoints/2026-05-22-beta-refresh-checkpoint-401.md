# Beta Refresh Checkpoint 401

## Goal

Make the Qwen multimodal promotion gate expose whether each required live proof
script exists, without changing the supported-model boundary.

## Changes

- Added `promotionProofExistence`, `promotionProofExistenceCount`, and
  `promotionProofExistenceParity` to
  `/qa/gap-ledger.gapContracts.qwenMultimodalRuntime`.
- Mirrored the same existence map/count/parity through top-level
  `/qa/gap-ledger`, `/qa/audit-ledger`, and
  `/qa/coverage-index.groups.appStateAndAudit`.
- Strengthened the gap-ledger, audit-ledger, coverage-index, and broad app QA
  matrix proofs so Qwen multimodal promotion remains blocked until the live
  loader, prefix-cache, and context-routing proof scripts exist and pass.
- Updated the system review and flow inventory with the promotion proof
  existence contract.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red gap-ledger proof failed because the route named the missing Qwen
multimodal live proofs but did not expose per-proof existence status. The green
path keeps Qwen VL/multimodal blocked while making the promotion gate visible to
the app, audit rollup, and top-level QA index.
