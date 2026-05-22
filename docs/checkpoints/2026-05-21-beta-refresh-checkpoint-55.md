# Checkpoint 55 - Tool Execution Cancel Proof

## Summary

Extended live-turn QA from stream cancellation into subprocess cancellation.
The app now exposes live tool-executor state to the QA server and marks active
tool cards as canceled when the user stops a running command.

## Changes

- Added a mock-model branch that emits a `run_shell` tool call for a long
  command:
  `printf tool-start; sleep 10; printf tool-final-marker`.
- Extended `scripts/live-turn-harness.py` to:
  - wait until `/state.toolExecutor.isRunning` is true;
  - call `/stop`;
  - wait for the conversation loop to leave `isWorking`;
  - assert the `run_shell` card status contains `canceled`;
  - assert only pre-stop output can appear after the displayed command line.
- Extended TestServer `/state` with:
  - `toolExecutor.isRunning`;
  - `toolExecutor.currentTool`;
  - bounded `toolExecutor.currentOutput`.
- Updated `ChatService.stop()` to mark any `running...` tool card as
  `canceled` and append `Stopped by user.` to the card body.
- Updated the system review matrix and migration ledger.

## Verification

```bash
python3 scripts/live-turn-harness.py
```

## Remaining Work

- Add per-tab action state and visual proof for running/progress/done/error.
- Add model-callable catalogue search.
- Add real Qwen and MiniMax model-folder live-turn scripts.
