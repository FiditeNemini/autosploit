# Checkpoint 218 - Session Coverage State Keys

## Goal

Make `/qa/session-coverage` expose the `/state` keys behind cross-app workflow
proofs for onboarding, mode selection, Sidebar actions, overlays, model-folder
pickers, persistence, tabs, phases, and Activity Feed controls.

## Changes

- Strengthened `scripts/session-coverage-proof.py` to require session
  `stateKeys`.
- Updated `GET /qa/session-coverage` with the AppState keys used by the session
  workflow proof scripts.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing session state-key accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/session-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/session-coverage` listed routes, proofs, and
contracts but did not expose the `/state` keys those proofs validate. The green
path adds that state-key contract.
