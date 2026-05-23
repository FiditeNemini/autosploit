# Beta Refresh Checkpoint 410

## Goal

Make the Creds tab's credential rows, hash-crack action, copy actions,
lifecycle state, and activity telemetry auditable from one QA route.

## Changes

- Added `/qa/creds-coverage` for parsed credential rows, Hash Crack, copy paths
  for cracking/bruteforce/secrets/vault, cracking/bruteforce/secrets lifecycle
  state, and activity telemetry.
- Exposed Creds surface, route, state-key, proof, and contract metadata with
  list/count/parity fields.
- Mirrored the Creds coverage route through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Added `scripts/creds-coverage-proof.py` and strengthened coverage-index and
  broad app matrix proofs to keep Creds action/copy/lifecycle flow wired.
- Updated the system review and flow inventory docs with the route and mirror
  behavior.

## Proof

- `python3 scripts/creds-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/creds-coverage` did not exist. The green path
makes Creds hash-crack actions, copy paths, parsed credential rows, lifecycle
strips, and activity visibility measurable from both the source route and the
top-level tabs/session aggregate.
