# Checkpoint 391 - Release Notary Gate Metadata

## Goal

Make beta release readiness distinguish signed/package readiness from
notarization readiness with machine-readable notary-gate metadata.

## Changes

- Added `notarizationGate`, `notaryProfileRequired`, and
  `notarizationGateReason` to `release/release-manifest.json` generation.
- Added skip-notarize and signature-verification commands to the release
  manifest command map.
- Extended `/qa/release-readiness` to require and expose the notary gate fields.
- Mirrored notary gate metadata and release commands through
  `/qa/coverage-index.groups.releaseReadiness`.
- Extended `scripts/release-readiness-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py` to enforce the contract.
- Updated the beta release readiness document with the structured notary gate.

## Proof

- `python3 scripts/release-readiness-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red release proof failed because the generated manifest only contained the
notarization status and notarize command. The red coverage-index proof then
failed because the release group did not mirror the new notary gate metadata.
