# Checkpoint 392 - Live Proof Failure Classification

## Goal

Make failed live-proof artifacts actionable by separating known legacy failures
from current unclassified live-proof regressions.

## Changes

- Added `knownFailedLiveProofs`, `knownFailedLiveProofCount`,
  `currentFailedLiveProofs`, `currentFailedLiveProofCount`, and
  `currentLiveProofFailureFree` to `/qa/artifact-ledger`.
- Classified `docs/live-proofs/checkpoint-75-minimax-live.json` as the known
  legacy MiniMax OOM live proof artifact.
- Mirrored the classification through `/qa/audit-ledger` and
  `/qa/coverage-index.groups.appState`.
- Extended `scripts/artifact-ledger-proof.py`,
  `scripts/audit-ledger-proof.py`, `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py` to enforce the classification.
- Updated the app system review and flow inventory docs.

## Proof

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red artifact-ledger proof failed because the ledger only exposed failed live
proof paths. The red audit proof then failed because the new classification was
not mirrored through `/qa/audit-ledger`.
