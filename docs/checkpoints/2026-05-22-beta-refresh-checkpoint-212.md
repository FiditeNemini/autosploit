# Checkpoint 212 - Runtime Live Proof Artifact Metadata

## Goal

Make `/qa/runtime-coverage` expose the checked-in live proof artifacts behind
the Qwen and MiniMax runtime/cache claims.

## Changes

- Strengthened `scripts/runtime-coverage-proof.py` to require live proof
  artifact paths for MiniMax restart replay, MiniMax block-L2 replay, MiniMax
  no-thinking, Qwen hybrid block-L2 plus SSM replay, Qwen full-prefix skip, and
  Qwen catalogue-prefix shape.
- The same proof now verifies each artifact exists, has `ok=true`, and includes
  the expected family report.
- Updated `GET /qa/runtime-coverage` with `liveProofArtifacts`.
- Updated docs with runtime live-proof artifact coverage.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `cd ExploitBotEngine && uv run --extra dev ../scripts/engine-no-model-metadata-proof.py`
- `python3 scripts/live-cache-stats-ui-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/runtime-coverage` exposed live-proof category
booleans but not the concrete artifact paths. The green path makes the real
Qwen/MiniMax cache and parser proof files auditable from the runtime aggregate.
