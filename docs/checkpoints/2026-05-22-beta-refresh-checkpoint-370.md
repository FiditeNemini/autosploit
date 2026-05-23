# Checkpoint 370 - Runtime Proof File Parity

## Goal

Make `/qa/runtime-coverage` expose proof-file parity and mirror that flag
through `/qa/coverage-index.groups.runtimeAndCache`.

## Changes

- Added `proofFileParity` to `/qa/runtime-coverage`.
- Added `runtimeProofFileParity` to the runtime/cache coverage-index aggregate.
- Extended `scripts/runtime-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/runtime-coverage` listed runtime/cache proof
scripts for model-folder autodetect, parser autodetect, prefix/L2/TurboQuant
cache contracts, unsupported-start blocking, and live-model cache verification
without a route-owned machine-readable parity flag proving those files exist.
