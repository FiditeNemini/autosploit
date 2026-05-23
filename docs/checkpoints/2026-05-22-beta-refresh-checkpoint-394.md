# Beta Refresh Checkpoint 394

## Goal

Expose Qwen multimodal promotion gates directly from the source gap ledger so UI, audit, and coverage consumers can render the blocked live-proof requirements without unpacking nested contract data.

## Changes

- Added top-level `/qa/gap-ledger` fields for Qwen multimodal promotion readiness, promotion criteria count, missing promotion criterion IDs, and missing live proof names.
- Refactored `/qa/audit-ledger` and `/qa/coverage-index.groups.appState` to mirror those fields from the source gap ledger.
- Strengthened gap, audit, coverage-index, and app QA matrix proofs around the source-level promotion gate fields.
- Updated the system review and flow inventory docs with the direct promotion-gate fields.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red gap proof first failed because the promotion gates existed only inside `gapContracts.qwenMultimodalRuntime`. The green path keeps the nested contract intact while making the blocked promotion criteria first-class gap-ledger fields.
