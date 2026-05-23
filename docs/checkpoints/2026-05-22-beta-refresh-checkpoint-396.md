# Beta Refresh Checkpoint 396

## Goal

Make runtime live-proof artifact file parity visible from the runtime coverage route and mirrored by the top-level coverage index.

## Changes

- Added `liveProofArtifactFileParity` to `/qa/runtime-coverage`.
- Mirrored the live proof artifact file-parity flag through `/qa/coverage-index.groups.runtimeAndCache`.
- Strengthened runtime, coverage-index, and app QA matrix proofs so runtime live artifact maps require real checked-in files.
- Updated the system review and flow inventory documentation with the runtime live artifact file-parity contract.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red runtime proof failed because live proof artifacts were listed and counted but lacked a direct file-parity flag. The green path keeps the existing artifact content checks while making artifact presence machine-readable for QA summaries.
