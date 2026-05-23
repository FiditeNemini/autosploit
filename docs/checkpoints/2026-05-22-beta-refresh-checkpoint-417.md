# Beta Refresh Checkpoint 417

## Goal

Make saved evidence, findings, stash notes, reports, and model context flow
auditable as one lifecycle instead of only as separate tab-specific proofs.

## Changes

- Added `scripts/evidence-lifecycle-coverage-proof.py`.
- Added `/qa/evidence-lifecycle-coverage` with lifecycle stages, storage
  targets, handoffs, routes, proof parity, and bounded context policy.
- Mirrored the lifecycle contract into
  `/qa/coverage-index.groups.chatAndContext`.
- Added the route to `/state.qaCoverage.stateRoutes`.
- Updated the coverage-index and app matrix proofs to require the lifecycle
  endpoint and its index mirror.
- Updated the system review and flow inventory docs with the explicit
  evidence-to-context/report lifecycle.

## Proof

- `python3 scripts/evidence-lifecycle-coverage-proof.py`

## Notes

The red proof failed because parser, finding, stash, report, and context flows
were proven separately but not exposed as one route-owned lifecycle. The green
path now documents and proves the anti-context-flooding contract: evidence is
stored and retrievable, while routine model turns stay bounded and rely on
`search_context` for targeted retrieval.
