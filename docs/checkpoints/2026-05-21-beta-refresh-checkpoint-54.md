# Checkpoint 54 - Reasoning-Off And Stop Stream Proof

## Summary

Extended the live-turn mock harness to cover two turn-control paths that were
still only listed as required proof: reasoning disabled requests and explicit
stream cancellation.

## Changes

- `scripts/live-turn-harness.py` now records the latest mock request for
  post-turn assertions.
- The mock engine now respects `enable_thinking`; reasoning chunks are emitted
  only when the app requests thinking.
- Added a reasoning-off live turn that proves:
  - `enable_thinking` is `false`;
  - `chat_template_kwargs.enable_thinking` is `false`;
  - no thinking message is created.
- Added a slow-stream live turn that calls `/stop` and verifies the app leaves
  both streaming and working states before the mock can emit
  `slow-final-marker`.
- The mock engine now treats broken pipes and connection resets as normal
  cancellation instead of printing server tracebacks.
- `/state` now exposes `isWorking` so live QA can assert the full conversation
  loop state, not just token streaming.
- Updated the system review matrix with the new coverage.

## Verification

```bash
python3 scripts/live-turn-harness.py
```

## Remaining Work

- Add stop/cancel proof during a long-running tool execution.
- Add per-tab action state and visual proof for running/progress/done/error.
- Add real Qwen and MiniMax model-folder live-turn scripts once the next engine
  slice is ready.
