# Checkpoint 53 - Live Turn Mock Model Harness

## Summary

Added a deterministic live-turn harness that proves the Swift app can drive a
model-style chat loop through context, streaming, reasoning, usage metrics, tool
calls, and agentic modes without loading a large local model for every QA run.

## Changes

- Added `scripts/live-turn-harness.py`.
- Added QA server routes in `TestServer`:
  - `/engine/mock` connects chat to a mock OpenAI-compatible engine URL.
  - `/qa/seed-context` seeds ports, web host, vuln, stash, and CVE context.
  - `/reasoning` toggles reasoning.
  - `/approve` and `/reject` drive copilot tool approval.
- Extended `/state` to expose mock-connected model and context catalogue state.
- Updated the system review matrix with the new proof coverage.

## What The Harness Proves

The harness launches the app, starts a streaming mock engine, and verifies:

- the app sends `enable_thinking`;
- the app sends the OpenAI-compatible tools schema;
- the outbound chat request contains `Dynamic Context Catalogue`;
- seeded Apache 2.4.49 context reaches the model request;
- streamed reasoning content is accepted;
- streamed usage updates token/s and TTFT counters;
- `search_cve` executes in autopilot;
- manual mode converts a tool call into a suggested command;
- copilot mode shows approval and executes after `/approve`.

## Verification

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
git diff --check
```

## Remaining Work

- Add the no-reasoning assertion to the mock harness.
- Add stop/cancel streaming and tool execution assertions.
- Add per-tab tool action state from `onToolStart` and `onToolComplete`.
- Add real Qwen and MiniMax model-folder live-turn scripts.
