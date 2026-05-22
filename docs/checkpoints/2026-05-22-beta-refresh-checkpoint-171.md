# Beta Refresh Checkpoint 171

## Scope

- Prove the chat deploy-agent sheet is AppState-owned and visible through the
  agent action API.
- Keep the visible sheet lifecycle tied to the same deploy path that creates an
  agent and sends its task prompt when an engine is running.

## Changes

- Added `isDeployAgentSheetVisible` to `AppState`.
- Added `deploySheetVisible` to `/state.agentActions`.
- Added `openDeployAgentSheet`, `cancelDeployAgentSheet`, and
  `confirmDeployAgent`.
- Wired `ChatPanelView` deploy buttons, sheet dismissal, cancel, and deploy
  actions through AppState.
- Added `/qa/agent-deploy-sheet`.
- Added `scripts/agent-deploy-sheet-proof.py`.

## Proof

- Red proof first:
  `python3 scripts/agent-deploy-sheet-proof.py` failed because
  `/qa/agent-deploy-sheet` did not exist.
- Green proof:
  `python3 scripts/agent-deploy-sheet-proof.py` passed.
- Agent action regression:
  `python3 scripts/agent-actions-proof.py` passed.
- Agent task-send regression:
  `python3 scripts/agent-deploy-task-send-proof.py` passed.
- Build proof:
  `swift build --package-path ExploitBot` passed.

## Note

- The proof uses `AgentType.rawValue`; the Recon type is surfaced as
  `Recon Agent`.

