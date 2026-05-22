# Checkpoint 198 - Agent Loop Coverage Routes

## Goal

Make `/qa/agent-loop-coverage` expose the full agentic-loop route, contract, and
proof surface rather than only high-level mode names.

## Changes

- Strengthened `scripts/agent-loop-coverage-proof.py` to require:
  - agent loop routes for mode switching, deploy-agent, agent actions, deploy
    sheet, settings actions, and app settings apply
  - contract flags for manual/copilot/autopilot behavior, deployed-agent forced
    autopilot, runtime/generation/reasoning/max-iteration inheritance,
    `search_context`, deploy-sheet, task-send, and settings controls
  - proof file existence checks and a proof count
- Updated `GET /qa/agent-loop-coverage` with the route list, contract flags,
  proof count, and deploy-sheet/task-send proof references.
- Added the deploy-sheet and task-send proof scripts to `/qa/coverage-index`.

## Proof

```bash
python3 scripts/agent-loop-coverage-proof.py
python3 scripts/coverage-index-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
swift build --package-path ExploitBot
git diff --check
```

## Notes

The red proof failed because `/qa/agent-loop-coverage` omitted
`agent-deploy-sheet-proof.py`, `agent-deploy-task-send-proof.py`, and the route/
contract metadata needed to audit the deployed-agent control surface.
