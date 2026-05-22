# Checkpoint 360 - Agent Loop Telemetry Field Count

## Goal

Make `/qa/agent-loop-coverage` own the action telemetry field count and mirror
that count through `/qa/coverage-index.groups.tabsAndSessions`.

## Changes

- Added `actionTelemetryFieldCount` to `/qa/agent-loop-coverage`.
- Updated `agentLoopActionTelemetryFieldCount` in the tabs/sessions
  coverage-index aggregate to consume the route-owned count.
- Extended `scripts/agent-loop-coverage-proof.py`,
  `scripts/coverage-index-proof.py`, and
  `scripts/app-qa-matrix-smoke-proof.py`.
- Updated the app flow inventory and system review docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-loop-coverage` exposed the action
telemetry field list without a machine-readable count owned by that same route.
