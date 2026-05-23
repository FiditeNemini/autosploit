# Beta Refresh Checkpoint 419

## Goal

Expose a source-owned endpoint inventory so every AppState test-server route is
grouped, documented, mirrored into coverage, and tied to a proof owner.

## Changes

- Added `scripts/endpoint-inventory-proof.py`.
- Added `/qa/endpoint-inventory`.
- Added `/qa/endpoint-inventory` to `/state.qaCoverage.stateRoutes`.
- Mirrored endpoint inventory counts, groups, routes, proofs, and proof-file
  parity into `/qa/coverage-index.groups.appState`.
- Updated the coverage-index and app matrix proofs to require the endpoint
  inventory route and mirror.
- Updated the system review and flow inventory docs with the endpoint inventory
  contract.

## Proof

- `python3 scripts/endpoint-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/endpoint-inventory` did not exist. The green
path keeps `AppState.swift` as the authority by parsing route cases directly
and using coverage-index mirrors only as secondary evidence.
