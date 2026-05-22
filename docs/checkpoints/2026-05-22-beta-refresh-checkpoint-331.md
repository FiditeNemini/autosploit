# Checkpoint 331 - Audit Gap Source Detail

## Goal

Make `/qa/audit-ledger` preserve the detailed source-derived gap warning
fields from `/qa/gap-ledger`, then mirror those audit fields through the
top-level coverage index.

## Changes

- Added `gapSource`, `gapSourceDerived`, `gapSourcePathExists`, and
  `currentGaps` to `/qa/audit-ledger`.
- Added `gapSupportedFamilies` and `unsupportedMultimodalBlocked`.
- Mirrored those audit fields into `/qa/coverage-index.groups.appState` as
  `auditGapSource`, `auditGapSourceDerived`, `auditGapSourcePathExists`,
  `auditCurrentGaps`, `auditGapSupportedFamilies`, and
  `auditUnsupportedMultimodalBlocked`.
- Extended `scripts/audit-ledger-proof.py`, `scripts/coverage-index-proof.py`,
  and `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red audit-ledger proof failed because `/qa/audit-ledger` only carried gap
count, next-gap text, open IDs, and contracts. The green path keeps the
Qwen/MiniMax-only support boundary and Qwen multimodal block status visible from
both the audit rollup and the top-level coverage index.
