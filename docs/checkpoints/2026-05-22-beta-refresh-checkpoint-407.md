# Beta Refresh Checkpoint 407

## Goal

Make durable stash notes and bounded context handoff auditable from one QA route
instead of relying only on scattered Stash action and retrieval proofs.

## Changes

- Added `/qa/stash-coverage` for manual note creation, add-sheet creation,
  filtering, copying, bounded send-to-chat, deletion, row context actions,
  active-scope retrieval, dynamic context catalogue sourcing, and activity
  telemetry.
- Exposed Stash surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Stash coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/stash-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Stash storage and context handoff wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/stash-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/stash-coverage` did not exist. The green path
makes saved notes, stash CRUD, bounded chat handoff, active-scope retrieval, and
dynamic catalogue participation visible from both the source route and the
top-level tabs/session aggregate.
