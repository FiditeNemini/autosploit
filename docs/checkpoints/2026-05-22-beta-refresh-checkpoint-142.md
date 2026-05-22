# Checkpoint 142 - Agent Control Actions

## Scope

- Make multi-agent deploy, switch, remove, and clear controls observable through
  AppState instead of direct `AgentManager` mutations from views.

## Changes

- Added `AgentActionState` and exposed it as `/state.agentActions`.
- Added deterministic QA routes `/qa/seed-agent-actions` and
  `/qa/agent-action`.
- Routed Chat agent tab switching/removal, Sidebar agent switching, and Settings
  agent removal/clear controls through AppState wrappers.
- Added `scripts/agent-actions-proof.py`.

## Verification

- `python3 scripts/agent-actions-proof.py`
- `python3 scripts/agent-autopilot-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies agent count, active-agent selection, deploy/switch/remove/
  clear telemetry, and activity-feed visibility for each agent-control action.
