# Checkpoint 388 - Coverage Group Health Contract

## Goal

Make every `/qa/coverage-index` group directly scannable for health and proof
file parity so the top-level QA ledger can be audited without bespoke per-group
knowledge.

## Changes

- Added normalized `ok` and `proofFileParity` fields to every
  `/qa/coverage-index.groups.*` payload.
- Extended `scripts/coverage-index-proof.py` to require group health, proof file
  parity, endpoint count parity, and proof count parity for every group.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to enforce the same normalized
  group contract in the app-wide smoke gate.

## Proof

- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red coverage proof failed because the `releaseReadiness` group did not
expose normalized `ok` and `proofFileParity` fields. The fix was applied in the
shared coverage-index group builder, so all coverage groups now carry the same
health contract.
