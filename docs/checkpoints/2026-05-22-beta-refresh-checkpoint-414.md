# Beta Refresh Checkpoint 414

## Goal

Make the Recon tab's Full Recon action state, parsed result groups, copy paths,
and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/recon-coverage` for Full Recon action state, subdomain rows, port
  rows, web-host rows, crawl rows, OSINT rows, copy paths for each Recon result
  type, and activity telemetry.
- Exposed Recon surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Recon coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/recon-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Recon action/copy/result flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/recon-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/recon-coverage` did not exist. The green path
makes Recon action state, parsed result groups, copy paths, and activity
visibility measurable from both the source route and the top-level tabs/session
aggregate.
