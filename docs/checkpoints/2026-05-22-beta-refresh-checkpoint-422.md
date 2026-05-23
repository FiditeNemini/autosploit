# Beta Refresh Checkpoint 422

## Goal

Expose a source-owned backend service inventory so service files, types, and
functions are grouped, documented, mirrored into coverage, and tied to proof
owners.

## Changes

- Added `scripts/service-inventory-proof.py`.
- Added `/qa/service-inventory`.
- Added `/qa/service-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for Swift files under
  `ExploitBot/Sources/ExploitBot/Services`.
- Added grouping and proof-owner mapping for agent/chat, context/evidence,
  runtime/model, tool/execution, persistence/reporting, and support services.
- Mirrored service file counts, type counts, function counts, group counts, and
  proof-file parity into `/qa/coverage-index.groups.appState`.
- Updated coverage-index and app matrix proofs to require the service inventory
  endpoint and mirror.
- Updated the system review and flow inventory docs with the service inventory
  contract.

## Proof

- `python3 scripts/service-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/service-inventory` did not exist. The green
path keeps the Services source tree as the authority and uses coverage-index as
the mirror, so future service-layer additions must appear in the source-derived
inventory.
