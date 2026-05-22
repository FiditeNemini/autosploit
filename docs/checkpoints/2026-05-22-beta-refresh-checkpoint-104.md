# Checkpoint 104: Context Window Cache Preservation

## Scope

- Make the app's "new context window" behavior explicit in `/state`.
- Prove the visible chat/session reset does not disable the prefix-cache,
  prompt-L2, paged-cache, block-L2, TurboQuant KV cache response path, or
  model-folder generation defaults.

## Changes

- `ChatService` now tracks `contextWindowGeneration` and increments it when a
  new visible context window starts.
- `/state.contextWindow` now reports:
  - context generation;
  - whether the running engine session is preserved;
  - `cacheResponsesMethod=prefix-cache-l2-turboquant` when the required cache
    stack is enabled;
  - prefix cache, prompt L2, paged cache, block L2, TurboQuant KV, and
    model-generation-default flags.
- Added `scripts/context-window-cache-proof.py`.

## Proof

Command:

```bash
python3 scripts/context-window-cache-proof.py --output docs/live-proofs/checkpoint-104-context-window-cache-proof.json
```

Result:

- `/state.contextWindow.generation` increments from `0` to `1`.
- Visible messages clear.
- Prompt, completion, and cached-token counters reset.
- Previous request-context preview clears.
- Engine config is unchanged.
- Parsed engine cache stats are unchanged.

## Boundary

This proves app/session-level context reset with cache topology preserved. It is
not a real-model cross-run block-L2 replay proof, and it does not close the
separate Qwen hybrid background async rederive execution gate.
