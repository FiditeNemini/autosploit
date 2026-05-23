# Checkpoint 386 - Per-Tab Proof Family Audit Rollup

## Goal

Carry the per-tab proof family map through audit and matrix coverage so the
individual tab audit surface is visible from every top-level QA ledger.

## Changes

- Mirrored `/qa/proof-ledger.tabProofFamilies` through `/qa/audit-ledger`.
- Mirrored the audit copy through `/qa/coverage-index.groups.appState`.
- Extended `scripts/audit-ledger-proof.py` to require exact proof-ledger tab
  family parity.
- Extended `scripts/coverage-index-proof.py` to require exact audit tab family
  parity.
- Extended `scripts/app-qa-matrix-smoke-proof.py` to enforce both direct audit
  parity and coverage-index audit parity.

## Proof

- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`

## Notes

The red audit proof failed because `/qa/audit-ledger` did not yet mirror
`tabProofFamilies` from `/qa/proof-ledger`.
