# Checkpoint 155 - Agent Deploy Task Send

## Scope

- Make multi-agent deployment telemetry prove whether an initial task prompt was
  sent into the deployed agent chat.

## Changes

- Added `taskSent`, `messageCount`, and `stoppedGeneration` to
  `/state.agentActions`.
- `deployAgent` now records agent action state after the optional task send so
  the action state exposes whether the task was sent and how many agent messages
  exist.
- Agent timeout stop now records `timeoutStop` with `stoppedGeneration: true`.
- Added `scripts/agent-deploy-task-send-proof.py`.

## Verification

- `python3 scripts/agent-deploy-task-send-proof.py`
- `python3 scripts/agent-actions-proof.py`
- `python3 scripts/agent-settings-actions-proof.py`
- `python3 scripts/agent-autopilot-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof uses a mock engine state, deploys a new agent with a task, and
  verifies both `/state.agentActions` and the agent detail row expose the sent
  task message.
