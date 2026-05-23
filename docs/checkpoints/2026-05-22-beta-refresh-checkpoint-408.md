# Beta Refresh Checkpoint 408

## Goal

Make the Web tab's vulnerability rows, finding/stash handoff, related CVE
search, and Verify progress auditable from one QA route.

## Changes

- Added `/qa/web-coverage` for Web vulnerability rows, Create Finding, Stash,
  Copy, Copy All, Header Copy, row context actions, related-CVE search, Verify
  progress, context handoff, and activity telemetry.
- Exposed Web surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Web coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/web-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Web vuln-to-finding/context flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/web-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/web-coverage` did not exist. The green path
makes Web vulnerability surfaces, finding/stash/copy actions, related CVE
search, Verify progress, context handoff, and activity visibility measurable
from both the source route and the top-level tabs/session aggregate.
