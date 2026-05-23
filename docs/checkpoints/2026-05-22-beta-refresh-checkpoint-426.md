# Beta Refresh Checkpoint 426

## Goal

Expose a source-owned agentic turn-flow inventory so the model turn loop,
context catalogue injection, tool schema ranking, streaming, reasoning and
usage metrics, tool authorization, tool execution, result ingestion, activity
telemetry, phase advancement, loop continuation, and cancellation paths are
grouped, documented, mirrored into coverage, and tied to proof owners.

## Changes

- Added `scripts/agent-flow-inventory-proof.py`.
- Added `/qa/agent-flow-inventory`.
- Added `/qa/agent-flow-inventory` to `/state.qaCoverage.stateRoutes`.
- Added source parsing for the Swift files that own the agentic turn loop:
  `ChatService`, `AgentManager`, `ToolDefinitions`, `ToolExecutor`,
  `ResultsStore`, `ContextCatalogService`, `ActivityFeed`, and AppState wiring.
- Added grouping and proof-owner mapping for conversation loop, agent manager,
  tool catalogue, tool execution, result ingestion, context catalogue, activity
  telemetry, and AppState wiring.
- Added phase-token coverage for send guard, context catalogue, tool schema
  ranking, stream completion, reasoning/metrics, tool-call accumulation,
  manual suggestion, copilot approval, scope enforcement, built-in callback
  execution, subprocess execution, result ingestion, activity telemetry, phase
  advance, loop continuation, and stop/cancel.
- Mirrored file counts, type counts, function counts, callback counts, group
  counts, flow phase list, phase parity, and proof-file parity into
  `/qa/coverage-index.groups.chatAndContext`.
- Updated coverage-index and app matrix proofs to require the agent-flow
  inventory endpoint and mirror.
- Updated the system review and flow inventory docs with the agent-flow
  inventory contract.

## Proof

- `python3 scripts/agent-flow-inventory-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red proof failed because `/qa/agent-flow-inventory` did not exist. The
green path keeps the Swift source files that own the model/tool loop as the
authority and uses the coverage index as the mirror, so future agent-loop,
tool-call, context, result-ingestion, telemetry, or cancellation changes must
remain visible in the source-derived inventory.
