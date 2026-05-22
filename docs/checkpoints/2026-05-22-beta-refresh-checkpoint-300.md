# Checkpoint 300 - Agent Loop Phase Proof Map

## Goal
Tie each machine-readable agent-loop phase to concrete proof scripts.

## Changes
- Added `/qa/agent-loop-coverage.loopPhaseProofs`.
- Added `loopPhaseProofCount` and `loopPhaseProofParity`.
- Mirrored phase-proof count/parity into
  `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened the agent-loop and coverage-index proofs.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red agent-loop proof failed because the endpoint named the loop phases but
did not map each phase to the scripts that prove it. The green path maps prompt
receipt, dynamic context retrieval, schema selection, streaming, tool parsing,
mode policy, scope enforcement, execution, result storage, and loop re-entry to
the focused live-turn, fanout, mode, parser, and agent proofs.
