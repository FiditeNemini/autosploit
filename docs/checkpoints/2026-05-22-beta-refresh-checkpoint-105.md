# Checkpoint 105: Visible Context Cache Status

## Scope

- Surface the active context-window generation and cache-preserved state in the
  chat panel.
- Extend the visual proof so the seeded chat screen includes this status
  alongside reasoning, tool execution, token, context, and tool-schema states.

## Changes

- Chat header now shows `ctx N` for the active visible context window.
- When the engine is running and parsed cache stats confirm TurboQuant KV is
  active, the header shows `cache preserved`.
- QA chat visual seeding now sets a nonzero context generation, running engine
  state, required cache defaults, and parsed cache stats.
- `scripts/visual-chat-proof.py` now requires:
  - `/state.contextWindow.generation == 2`;
  - `/state.contextWindow.engineSessionPreserved == true`;
  - `/state.contextWindow.cacheResponsesMethod == prefix-cache-l2-turboquant`.

## Proof

Command:

```bash
python3 scripts/visual-chat-proof.py
```

Result:

- Refreshed screenshot:
  `docs/visual-proofs/checkpoint-71/chat-tool-states.png`
- Refreshed manifest:
  `docs/visual-proofs/checkpoint-71/manifest.json`

## Boundary

This is visible app-state proof. It does not claim a real-model cross-run
block-L2 replay or true Qwen hybrid async rederive execution.
