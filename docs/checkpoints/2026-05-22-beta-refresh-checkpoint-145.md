# Checkpoint 145 - Agent Settings Controls

## Scope

- Make Settings > Agents multi-agent enablement and max-concurrent controls
  route through AppState instead of direct `AgentManager` mutations.

## Changes

- Added `/qa/agent-settings-action` for deterministic settings-control proof.
- Added `setMultiAgentEnabled` and `setMaxConcurrentAgents` AppState wrappers.
- Routed Settings multi-agent toggle and max concurrent segmented control
  through the wrappers.
- Updated `applyAppSettings` to use the same wrappers.
- Added `scripts/agent-settings-actions-proof.py`.

## Verification

- `python3 scripts/agent-settings-actions-proof.py`
- `python3 scripts/agent-actions-proof.py`
- `python3 scripts/agent-autopilot-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies persisted settings surface through `/state.agents`, action
  telemetry through `/state.agentActions`, activity-feed visibility, and the
  full-agent clear when multi-agent mode is disabled.
