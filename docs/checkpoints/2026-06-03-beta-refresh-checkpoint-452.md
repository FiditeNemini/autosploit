# Checkpoint 452 - Startup Cache Defaults Gate

## Goal

Make startup cache topology a route-owned beta contract instead of relying on scattered settings and runtime proof assumptions.

## Changes

- Added `GET /qa/startup-cache-defaults`.
- Added `scripts/startup-cache-defaults-proof.py`.
- The route proves default parser, generation, TurboQuant KV, prefix cache, prompt L2 disk, paged cache, block L2 disk, cache memory, disk-cache sizing, and max-token values from app state.
- The route source-checks Settings apply behavior, persistent engine config load/save keys, and engine/server launch flags including parser flags, TurboQuant KV, cache flags, and `--max-num-seqs`.
- Mirrored startup cache/defaults parity through `/qa/settings-coverage` and `/qa/runtime-coverage`.

## Proof

- `python3 scripts/startup-cache-defaults-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/proof-category-matrix-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/docs-inventory-parity-proof.py`
- `git diff --check`

## Remaining

- This checkpoint is source/app-state-backed. It does not replace the separate live Qwen and MiniMax model stress proofs.
