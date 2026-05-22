# Checkpoint 299 - Agent Loop Phase Contract

## Goal
Make the model/tool loop shape machine-readable from the agent-loop QA surface.

## Changes
- Added `/qa/agent-loop-coverage.loopPhases`.
- Added `loopPhaseCount` and `loopPhaseParity`.
- Mirrored the phase contract into `/qa/coverage-index.groups.tabsAndSessions`.
- Strengthened the agent-loop and coverage-index proofs.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`

## Notes
The red agent-loop proof failed because `/qa/agent-loop-coverage` exposed modes,
agent inheritance, telemetry fields, and state keys, but not the actual phase
shape of a model/tool turn. The green path exposes receive prompt, dynamic
context retrieval, schema selection, streaming, tool-call parsing, mode policy,
scope enforcement, tool execution, result storage, and loop re-entry.
