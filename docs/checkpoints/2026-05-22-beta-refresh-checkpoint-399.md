# Beta Refresh Checkpoint 399

## Goal

Make session workflow state-key coverage countable and parity-checked from the source route and the top-level tabs/sessions coverage group.

## Changes

- Added `stateKeyCount` and `stateKeyParity` to `/qa/session-coverage`.
- Mirrored `sessionStateKeyCount` and `sessionStateKeyParity` through `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened session, coverage-index, and app QA matrix proofs so cross-app session workflows remain tied to their visible state surfaces.
- Updated the system review and flow inventory documentation with the session state-key count/parity contract.

## Proof

- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red session proof failed because `/qa/session-coverage` listed state keys but did not expose a count or parity flag. The green path makes onboarding, sidebar, overlay, persistence, phase, and activity workflow state coverage measurable from both the source route and aggregate coverage index.
