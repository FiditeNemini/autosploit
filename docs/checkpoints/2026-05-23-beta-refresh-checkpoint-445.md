# Beta Refresh Checkpoint 445

## Goal

Add an artifact manifest matrix so visual evidence manifests have row-level
ownership across the artifact ledger, visual surface matrix, runtime coverage,
and coverage index.

## Changes

- Added `scripts/artifact-manifest-matrix-proof.py`.
- Added `/qa/artifact-manifest-matrix`.
- Added `/qa/artifact-manifest-matrix` to `/state.qaCoverage.stateRoutes`.
- Added one row per `/qa/artifact-ledger.visualManifests` entry with manifest
  existence, capture existence, capture count, `/qa/artifact-ledger`,
  `/qa/visual-surface-matrix`, and `/qa/runtime-coverage` linkage.
- Mirrored `artifactManifestMatrixCount`,
  `artifactManifestMatrixProofFileParity`,
  `artifactManifestMatrixManifestFileParity`, and
  `artifactManifestMatrixCaptureFileParity` into
  `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the new artifact
  manifest matrix route and mirrors.
- Updated the system review and flow inventory docs with the artifact manifest
  matrix contract.

## Proof

- `python3 scripts/artifact-manifest-matrix-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/proof-suite-inventory-proof.py`
- `python3 scripts/checkpoint-ledger-proof.py`

## Notes

The red proof failed because `/qa/artifact-manifest-matrix` did not exist. The
green path keeps every visual manifest tied to source artifact-ledger data,
visual surface coverage, runtime live-proof artifact counts, docs, and
coverage-index mirrors.
