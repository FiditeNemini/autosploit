# Checkpoint 385 - Per-Tab Proof Ledger Families

## Goal

Expose proof coverage by individual tab family so recon, web, network, creds,
exploit, post, osint, report, and stash can be audited directly instead of only
through the broad `tabs` category.

## Changes

- Added `/qa/proof-ledger.tabProofFamilies`.
- Added per-family proof counts and file-parity flags.
- Mirrored the tab proof family map, count, parity, and file parity through
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/proof-ledger-proof.py` with required representative proofs
  for every tab family.
- Extended `scripts/coverage-index-proof.py` to ensure the aggregate mirrors
  the proof ledger tab family data exactly.

## Proof

- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/proof-ledger` had tab-category proofs but no
per-tab family map.
