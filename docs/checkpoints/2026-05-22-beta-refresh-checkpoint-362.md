# Checkpoint 362 - Agent Loop Proof File Parity

## Goal

Make `/qa/agent-loop-coverage` expose proof-file parity and mirror that
flag through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `proofFileParity` to `/qa/agent-loop-coverage`.
- Added `agentLoopProofFileParity` to the tabs/sessions coverage-index
  aggregate.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` listed proof files without
a route-owned machine-readable parity flag proving those proof files exist.
