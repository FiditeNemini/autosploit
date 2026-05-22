# Checkpoint 213 - Runtime Live Proof Artifact Count

## Goal

Make `/qa/runtime-coverage` expose a machine-readable count for the checked-in
Qwen and MiniMax live proof artifacts.

## Changes

- Strengthened `scripts/runtime-coverage-proof.py` to require
  `liveProofArtifactCount`.
- Updated `GET /qa/runtime-coverage` to derive `liveProofArtifactCount` from the
  same `liveProofArtifacts` map returned by the endpoint.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level app QA
  matrix also catches missing runtime live artifact accounting.
- Updated review and flow docs with the new count contract.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/runtime-coverage` exposed artifact paths but
did not expose `liveProofArtifactCount`. The green path derives the count from
the artifact map to avoid path/count drift.
