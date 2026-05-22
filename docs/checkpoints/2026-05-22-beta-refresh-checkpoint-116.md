# Checkpoint 116: Deployed Agent Autopilot Proof

## Scope

- Prove deployed agents can run a real autonomous chat/tool loop through the
  same mock OpenAI-compatible stream path as the main chat.
- Make the QA mock-engine route behave like a running engine so deployed agents
  inherit runtime configuration and auto-start their task prompt.
- Expose proof-grade agent state through `/state`.

## Changes

- Added `scripts/agent-autopilot-proof.py`.
- Added QA route `POST /qa/deploy-agent`.
- Updated `POST /engine/mock` to set the engine manager's running state,
  loaded model, and port so agent deployment follows the same running-engine
  branch as production deployment.
- Added `/state.agents.details` with per-agent runtime, loop, prompt, context,
  tool-schema, and completion counters.
- Fixed typed-agent setup so phase guidance is set before appending the
  type-specific prompt override.
- Typed agents now seed their prompt-ranked tool lane from the agent type.

## Proof

Command:

```bash
python3 scripts/agent-autopilot-proof.py
```

Result:

- The proof first failed on missing `POST /qa/deploy-agent`.
- After wiring, the proof launches the app with an isolated data directory,
  attaches a streaming mock engine, enables multi-agent mode, deploys a Web
  agent, and waits for completion.
- The completed agent state proves:
  - `interactionMode=autopilot`;
  - `baseURL=http://127.0.0.1:18992`;
  - `modelName=mock-qwen-jang`;
  - `useModelGenerationDefaults=true`;
  - `maxIterations=6`;
  - `activeTab=web`;
  - type prompt override preserved;
  - bounded context snippets;
  - prompt-ranked tool schemas including `search_context`;
  - at least one executed tool call;
  - autonomous continuation after the tool result.

## Boundary

This is a deterministic mock-engine proof for agentic control-flow and app
state. Real-model cache/generation behavior remains covered by the Qwen and
MiniMax live-model proofs.
