# Beta Refresh Checkpoint 418

## Goal

Expose beta package readiness as one route-owned contract that combines signed
artifacts, proof ledgers, visual/live evidence, known gaps, and notarization
state.

## Changes

- Added `scripts/beta-readiness-coverage-proof.py`.
- Added `/qa/beta-readiness-coverage` with source-proof, visual-artifact,
  live-artifact, checkpoint, signed-app, signed-DMG, manifest, known-gap, and
  notarization-profile gates.
- Mirrored the beta readiness contract into
  `/qa/coverage-index.groups.releaseReadiness`.
- Added the route to `/state.qaCoverage.stateRoutes`.
- Updated coverage-index and app matrix proofs to require the beta readiness
  endpoint and index mirror.
- Updated the system review and flow inventory docs to distinguish
  `packageReady=true` from `distributionReady=false` before notarization.

## Proof

- `python3 scripts/beta-readiness-coverage-proof.py`

## Notes

The red proof failed because package readiness was split across release,
artifact, audit, and gap ledgers. The green path keeps those source ledgers as
the authority while adding a single beta readiness route. The current package
is signed and prepared; distribution remains gated on a local notarytool
profile plus successful notarization and stapling.
