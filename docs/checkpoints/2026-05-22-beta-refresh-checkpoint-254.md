# Checkpoint 254 - Audit Ledger Proof Categories

## Goal
Carry proof-category accounting into `/qa/audit-ledger` so the global audit
rollup mirrors `/qa/proof-ledger` beyond a single total proof count.

## Changes
- Updated `scripts/audit-ledger-proof.py` to require
  `proofCategoryCounts`, `proofCategoryTotalCount`, and
  `proofCategoryParity`.
- Added those fields to `/qa/audit-ledger` from the existing proof ledger
  snapshot.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes
The red proof failed because `/qa/audit-ledger` exposed only `proofCount`.
The green path makes the audit rollup carry the same proof-category counts,
total, and parity status as the proof and coverage ledgers, so proof-surface
distribution remains auditable from the global audit endpoint.
