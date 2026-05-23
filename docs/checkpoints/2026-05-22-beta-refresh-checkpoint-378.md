# Checkpoint 378 - Agent Loop Phase Proof File Parity

## Goal

Make `/qa/agent-loop-coverage` expose file parity for agent loop phase proof
maps and mirror that flag through the tabs/sessions coverage-index aggregate.

## Changes

- Added `loopPhaseProofFileParity` to `/qa/agent-loop-coverage`.
- Mirrored `agentLoopPhaseProofFileParity` through
  `/qa/coverage-index.groups.tabsAndSessions`.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` listed phase proof files
without an explicit route-owned file-parity flag for the mapped proof files.
