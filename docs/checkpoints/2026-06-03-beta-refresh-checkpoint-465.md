# Beta Refresh Checkpoint 465 - Superseded Live-Proof Classification

Date: 2026-06-03

## Goal

Clear the unclassified current live-proof failure without deleting or hiding the failed artifact. The ledger now keeps the failed Qwen MXFP JSON visible and only removes it from current failures when its passing replacement proof is present.

## Changes

- Added `supersededFailedLiveProofs` and `supersededReplacementStatus` to `/qa/artifact-ledger`.
- Mirrored the superseded live-proof fields through `/qa/audit-ledger`.
- Updated beta readiness so `liveArtifacts` is ready when all current failures are classified, while `distributionReady` remains false while known gaps remain.
- Documented the live artifact ledger behavior in `README.md`.

## Proof

Red path:

- `python3 scripts/artifact-ledger-proof.py`
- Expected failure before route wiring: `artifact ledger superseded failed live proof map mismatch`.

Green path:

- `python3 scripts/artifact-ledger-proof.py`
- `python3 scripts/audit-ledger-proof.py`
- `python3 scripts/beta-readiness-coverage-proof.py`

## Remaining

This classifies a superseded Qwen MXFP live-proof failure using `docs/live-proofs/checkpoint-486-qwen-mxfp-27b-pass.json` as the passing replacement. It does not close the known Qwen multimodal runtime promotion gap.
