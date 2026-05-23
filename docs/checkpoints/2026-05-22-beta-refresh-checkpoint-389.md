# Checkpoint 389 - Qwen Multimodal Promotion Gates

## Goal

Make the remaining Qwen multimodal/VL runtime gap auditable as explicit
promotion gates instead of a loose blocker note.

## Changes

- Added `promotionReady=false`, `promotionCriteria`,
  `promotionCriteriaCount`, `missingPromotionCriteriaIds`, and
  `missingPromotionProofs` to the `qwenMultimodalRuntime` gap contract.
- Required three missing promotion gates: real Qwen multimodal loader,
  multimodal prefix-cache key discipline, and multimodal context packet routing.
- Mirrored the normalized promotion fields through `/qa/audit-ledger` and
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/gap-ledger-proof.py`, `scripts/audit-ledger-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py` to enforce the promotion gate
  contract.
- Updated `docs/app-system-review-2026-05-21.md` so the human current-gap note
  matches the machine-readable ledger.

## Proof

- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red gap proof failed because `qwenMultimodalRuntime` did not expose
promotion readiness or the missing live proof gates. The red audit proof then
failed because the new gap fields were not mirrored through `/qa/audit-ledger`.
Both rollups now preserve the blocked state and the exact work required before
Qwen multimodal can be promoted into the supported beta lane.
