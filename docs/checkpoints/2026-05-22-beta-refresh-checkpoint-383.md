# Checkpoint 383 - Release Readiness Matrix Parity

## Goal

Promote release/package readiness from a focused QA surface into the top-level
app QA matrix so beta distribution evidence is checked with the rest of the app
coverage contract.

## Changes

- Extended `scripts/app-qa-matrix-smoke-proof.py` to request
  `/qa/release-readiness`.
- Required `/qa/release-readiness` in `/state.qaCoverage.stateRoutes`.
- Required the `release` proof-ledger category and
  `release-readiness-proof.py` membership.
- Required `/qa/coverage-index.groups.releaseReadiness` to mirror release
  proofs, artifacts, manifest-field parity, hash lengths, and the
  notary-profile gate.

## Proof

- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red matrix proof failed because it still expected the old eight proof
surfaces after the release proof category was added.
