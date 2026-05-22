# Checkpoint 194 - Chat Coverage Endpoint

## Goal

Expose chat, streaming-control, reasoning, tool-output, request-audit, and
context-window cache behavior through one machine-readable QA route.

## Changes

- Added `scripts/chat-coverage-proof.py`.
- Added `GET /qa/chat-coverage`, returning:
  - chat/control routes for Send, Stop, reasoning, approvals, visible new
    context, messages, and deterministic chat QA seeds/actions
  - contract flags for streaming usage metrics, token counters, reasoning
    toggle/collapse, tool-output expansion, approval controls, copy/stash
    actions, request-audit badges, context inspector state, scroll-lock visuals,
    tool-action chat control, and Stash-to-chat control
  - explicit `prefix-cache-l2-turboquant` cache-response method
  - explicit visible-new-context behavior:
    `clear-visible-chat-preserve-engine-cache-session`
  - linked visual manifests for chat metrics/tool states, scroll-lock/
    reasoning states, context inspector, and request-audit badges
  - proof scripts covering each contract
- Extended `scripts/app-qa-matrix-smoke-proof.py` to require the new route.
- Updated app flow and system review docs with the chat coverage route.

## Proof

```bash
python3 scripts/chat-coverage-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
```

## Notes

The red proof failed because `GET /qa/chat-coverage` did not exist. The green
proof verifies the route ties chat controls, reasoning/tool-output state,
visual scroll/context/audit captures, and cache-preserving new-context behavior
into one aggregate contract.
