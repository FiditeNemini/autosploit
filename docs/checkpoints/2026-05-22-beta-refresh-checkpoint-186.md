# Checkpoint 186 - Agent Loop Coverage Endpoint

## Goal

Expose the chat and deployed-agent loop contract through a machine-readable QA
route so manual, copilot, autopilot, and agent-autopilot behavior can be audited
from the app state.

## Changes

- Added `scripts/agent-loop-coverage-proof.py`.
- Added `GET /qa/agent-loop-coverage`, returning:
  - current interaction mode
  - max tool-loop iterations
  - manual/copilot/autopilot behavior contract
  - deployed-agent forced-autopilot and inheritance guarantees
  - proof scripts that cover the agent/tool-loop behavior
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route and
  validate the three mode behaviors.
- Updated the app flow and system review docs with the new audit route.

## Proof

```bash
python3 scripts/agent-loop-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/mode-selection-flow-proof.py
```

## Notes

The red proof failed because `GET /qa/agent-loop-coverage` did not exist. The
green proof verifies the route reflects live mode changes after `/mode manual`
and exposes the proof scripts for live-turn, mode-selection, tool fanout, and
deployed-agent context loops.
