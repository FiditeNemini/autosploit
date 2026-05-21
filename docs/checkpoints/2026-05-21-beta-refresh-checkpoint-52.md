# Checkpoint 52 - System Review And Chat Scroll Lock

## Summary

Added a whole-app review matrix and tightened chat scrolling into an explicit
lock/pause/relock behavior. This checkpoint focuses on the app-level flow
requirements around streaming smoothness, reasoning UI, metrics visibility,
tool loops, page wiring, and proof coverage.

## Changes

- Added `docs/app-system-review-2026-05-21.md`.
- Updated the app-flow inventory with current chat context, reasoning, metrics,
  and scroll-lock behavior.
- Added an explicit chat header scroll-lock button:
  - locked state follows newest streamed output;
  - dragging the chat history pauses auto-scroll;
  - paused state shows `Latest` or `New output`;
  - clicking the floating control relocks to the newest message.
- Sending a new message relocks the chat to the latest output.

## System Review Coverage

The system review matrix covers:

- engine startup and real-model proof requirements
- chat streaming, reasoning on/off, metrics, and stop behavior
- manual/copilot/autopilot tool loop expectations
- dynamic context and CVE embedding assist
- persistence and session boundaries
- tool result fanout into chat, activity feed, tab state, and context
- every tab's button wiring and missing proof
- automated, mock-model, real-model, and visual gates required for completion

## Remaining Work

- Add per-tab tool action state from `onToolStart` and `onToolComplete`.
- Add a mock model server for streaming/tool-call/mode tests.
- Add context catalogue fixture tests.
- Add live Qwen/MiniMax model load and chat proof scripts.
- Add a visible "context used" inspector in chat.

## Verification

Run after this checkpoint:

```bash
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
git diff --check
```

Visual QA should confirm the chat header shows the lock control and that the
scroll paused/relock affordance appears when auto-scroll is broken.
