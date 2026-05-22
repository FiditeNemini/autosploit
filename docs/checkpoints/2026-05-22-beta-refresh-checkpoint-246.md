# Checkpoint 246 - Structured Gap Contracts

## Goal
Make the remaining Qwen multimodal runtime gap machine-readable from both the
gap ledger and the global audit ledger.

## Changes
- Updated `scripts/gap-ledger-proof.py` to require `openGapIds` and a
  `qwenMultimodalRuntime` contract.
- Added structured `gapContracts` metadata to `/qa/gap-ledger`, including
  blocked model kinds, required runtime work, supported families, and proof
  scripts.
- Updated `scripts/audit-ledger-proof.py` and `/qa/audit-ledger` so the global
  audit rollup mirrors `openGapIds` and `gapContracts`.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red gap proof failed because `/qa/gap-ledger` only exposed prose and a
boolean for the blocked Qwen VL lane. The red audit proof then failed because
the global audit route did not roll up those gap details. The green path makes
the remaining multimodal gap visible as a stable contract while keeping the
Qwen/MiniMax text-family beta boundary explicit.
