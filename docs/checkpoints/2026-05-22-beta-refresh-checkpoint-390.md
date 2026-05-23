# Checkpoint 390 - Documentation Promotion Gate Parity

## Goal

Keep the human app inventory and system review synchronized with the
machine-readable Qwen multimodal promotion gates.

## Changes

- Added `scripts/docs-inventory-parity-proof.py` to require both
  `docs/app-system-review-2026-05-21.md` and
  `docs/app-flow-inventory-2026-05-21.md` to name the Qwen multimodal promotion
  gates and missing live proof scripts.
- Updated the app flow inventory to document the Qwen multimodal loader,
  multimodal prefix-cache key discipline, multimodal context packet routing,
  and the three required live proof script names.
- Expanded the system review current-gap note with the same missing proof names.
- Added the documentation parity proof to `/qa/coverage-index.groups.appState`.
- Extended `scripts/coverage-index-proof.py` and
  `scripts/app-qa-matrix-smoke-proof.py` to require the aggregate app-state
  group to carry the documentation parity proof.

## Proof

- `python3 scripts/docs-inventory-parity-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-ledger-proof.py`

## Notes

The red documentation proof first failed because the system review did not name
the exact missing live proof scripts and the flow inventory still described the
older Qwen multimodal gap contract. The red coverage-index proof then failed
because the new documentation parity proof was not listed in the aggregate
app-state proof group.
