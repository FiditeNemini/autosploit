# Beta Refresh Checkpoint 413

## Goal

Make the OSINT tab's parsed rows, screenshot artifacts, copy actions, artifact
row actions, lifecycle state, and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/osint-coverage` for username/email/metadata rows, screenshot
  artifacts, per-result copy actions, artifact row actions, lifecycle state, and
  activity telemetry.
- Exposed OSINT surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the OSINT coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/osint-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep OSINT row/artifact/copy/lifecycle flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/osint-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/osint-coverage` did not exist. The green path
makes OSINT rows, screenshot artifacts, copy paths, artifact row actions,
lifecycle strips, and activity visibility measurable from both the source route
and the top-level tabs/session aggregate.
