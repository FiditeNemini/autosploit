# Checkpoint 217 - Tab Action State Key Coverage

## Goal

Make `/qa/tab-action-coverage` expose the AppState action-state keys behind the
per-tab copy, stash, export, artifact, and tool action proofs.

## Changes

- Strengthened `scripts/tab-action-coverage-proof.py` to require
  `actionStateKeys`.
- Updated `GET /qa/tab-action-coverage` with the state surfaces for Recon, Web,
  Network, Creds, Exploit, Post, OSINT, Report, Stash, and tab activity.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing tab action state-key accounting.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/tab-action-coverage-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/tab-action-coverage` listed action routes,
contracts, and proofs but did not expose the `/state` keys those proofs validate.
The green path makes the aggregate auditable back to concrete AppState surfaces.
