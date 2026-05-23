# Beta Refresh Checkpoint 406

## Goal

Make the durable Report workflow auditable from one QA route instead of only
from scattered action proofs.

## Changes

- Added `/qa/report-coverage` for Report tab finding CRUD, preview generation,
  artifact export, report-agent draft, activity telemetry, durable finding
  storage, and context handoff.
- Exposed Report surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Report coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/report-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep the Report contract wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/report-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/report-coverage` did not exist. The green path
makes saved findings, report artifacts, report-agent drafting, activity
visibility, and context handoff visible from both the source route and the
top-level tabs/session aggregate.
