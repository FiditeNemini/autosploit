# Checkpoint 216 - Agent Loop Action Telemetry Coverage

## Goal

Make `/qa/agent-loop-coverage` expose the action telemetry fields that prove
agent deploy, task-send, status, progress, and visible activity behavior.

## Changes

- Strengthened `scripts/agent-loop-coverage-proof.py` to require the
  `actionTelemetryFields` contract.
- Updated `GET /qa/agent-loop-coverage` with the field list used by
  `/state.agentActions`.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing agent task-send telemetry.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/agent-loop-coverage-proof.py`
- `python3 scripts/agent-deploy-task-send-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/agent-loop-coverage` covered task-send as a
contract but did not expose the concrete action telemetry fields. The green path
makes those fields auditable from the aggregate route.
