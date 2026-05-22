# Checkpoint 58 - On-Demand Context Tool And Cache Session Proof

## Summary

Added a model-callable `search_context` tool backed by the dynamic context
catalogue. This lets the agent pull targeted assets, findings, stash notes,
recent tool output, and CVE context when needed instead of forcing every note
or embedding result into every prompt.

## Changes

- Added `search_context` to the model tool schema.
- Marked `search_context` as a callback tool, not a subprocess.
- Wired `ChatService.onSearchContext` into built-in tool execution.
- Centralized `search_context` wiring in `AppState.wireContextCatalog(...)` so
  the main chat and deployed agents share the same catalogue behavior.
- Bounded tool results to 1-8 snippets; the default is capped at 4 snippets.
- Added `ChatService.startNewContextWindow()` to clear chat history, in-flight
  state, and token counters without restarting the engine.
- Added TestServer `/context/new` and `/state.engineConfig` cache fields for
  live QA.
- Updated the chat clear confirmation copy to describe starting a fresh context
  window while preserving prefix and L2 cache topology.

## Verification

The live-turn harness now proves:

- the model sees `search_context` in the OpenAI-compatible tool schema;
- a model-issued `search_context` call returns the seeded Apache 2.4.49 and
  CVE-2021-41773 context from the ranked catalogue;
- prefix cache, prompt L2 disk cache, paged cache, block L2 disk cache,
  TurboQuant Q4 KV, and model-folder generation defaults remain enabled;
- `/context/new` clears chat messages while preserving the loaded model and
  cache defaults.

```bash
python3 scripts/live-turn-harness.py
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
```
