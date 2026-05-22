# Checkpoint 82 - Request Context Visibility

## Scope

- Make the dynamic context and bounded tool-schema selection visible rather than
  hidden request-shaping behavior.
- Keep the display compact enough for the chat panel.

## Changes

- `ChatService` now records the last dynamic context packet preview, selected
  snippet count, and exposed tool-schema names.
- `/state.requestContext` exposes `contextInjected`, `contextSnippetCount`,
  `contextPreview`, `toolSchemaCount`, and `toolSchemas` for live proof.
- The chat metrics strip shows compact `ctx N` and `tools N` counters with
  hover details.
- QA seeded chat state now includes request-context counters so screenshot proof
  covers the visual surface.

## Proof

- `swift build --package-path ExploitBot`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/visual-chat-proof.py`
- `git diff --check`

The live harness proves the request-context state appears after an agent turn,
stays bounded to 4 context snippets and 12 tool schemas or fewer, and still
preserves the prior streaming/tool/new-context cache behavior. The visual proof
refreshes `docs/visual-proofs/checkpoint-71/chat-tool-states.png` with token,
context, and tool-schema counters visible.

## Remaining

- Add a full expandable context/tool inspection panel for reviewing complete
  retrieved snippets and exposed schemas after each turn.
