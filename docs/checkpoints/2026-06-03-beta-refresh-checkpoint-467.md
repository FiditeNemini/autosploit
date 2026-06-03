# Beta Refresh Checkpoint 467 - Coverage False-Flag Classification

Date: 2026-06-03

## Goal

Make the remaining `/qa/coverage-index` false booleans auditable instead of
ambiguous. The beta status now separates known gaps, seeded-state requirements,
intentional negative policy checks, release distribution holds, local notary
profile semantics, bundled-runtime packaging facts, historical proof artifacts,
and unsupported-multimodal inventory state.

## Changes

- Added `/qa/coverage-false-flag-classification`.
- Added `scripts/coverage-false-flag-classification-proof.py`.
- Mirrored the new route, proof, false-flag count, classified count,
  unclassified count, classification buckets, and proof parity through
  `/qa/coverage-index.groups.appState`.
- Added the route to `/state.qaCoverage.stateRoutes`.
- Updated the README beta lane with the remaining false-flag classifier.

## Proof

Red path:

- `python3 scripts/coverage-false-flag-classification-proof.py`
- Expected failure before route wiring: `unknown: GET /qa/coverage-false-flag-classification`.

Green path:

- `python3 scripts/coverage-false-flag-classification-proof.py`
- `python3 scripts/coverage-index-proof.py`

The route classified all 40 live false booleans observed from
`/qa/coverage-index` with zero unclassified false flags.

## Remaining

This checkpoint does not make false rows pass. It makes their status explicit so
the beta gate can distinguish real open work from fixture-required or
intentionally false policy rows. The known Qwen multimodal runtime promotion gap
remains open.
