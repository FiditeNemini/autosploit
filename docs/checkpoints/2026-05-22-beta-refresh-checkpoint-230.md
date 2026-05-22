# Checkpoint 230 - Global Proof Ledger

## Goal

Expose a machine-readable ledger of all local proof scripts so exhaustive app,
tab, tool, runtime, visual, context, and agent-loop coverage can be audited from
the app QA API instead of only from scattered grouped summaries.

## Changes

- Added `scripts/proof-ledger-proof.py`.
- Added `GET /qa/proof-ledger`, dynamically discovering local proof scripts
  from `scripts/` and categorizing them by flow area.
- Added `/qa/proof-ledger` to `/state.qaCoverage.stateRoutes`.
- Added the proof-ledger route and `proofLedgerCount` to
  `/qa/coverage-index.groups.appState`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/proof-ledger-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof first failed because `/qa/proof-ledger` did not exist. After the
route was added, the proof exposed that the app process cwd is not always the
repo root; the green path resolves `scripts/` by walking upward from both cwd
and the Swift source file path.
