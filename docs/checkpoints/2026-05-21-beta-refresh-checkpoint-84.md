# Checkpoint 84 - Chat Request Context Inspector

## Scope

- Make the context/tool selection behind a model request inspectable in the chat
  panel, not only counted in the metrics strip.

## Changes

- `ChatService` now tracks whether the request-context inspector is expanded.
- The chat metrics strip includes an inspector toggle when a context packet or
  tool schemas exist.
- `RequestContextInspector` renders the bounded context packet preview and the
  exposed tool schema names below the metrics strip.
- QA route `/qa/chat-context-inspector` toggles the inspector for screenshot
  proof.
- Added `scripts/visual-context-inspector-proof.py`.
- Tightened `scripts/live-turn-harness.py` so repeated mock `search_context`
  turns do not make the proof depend on the latest card being the completed
  card.

## Proof

- `swift build --package-path ExploitBot`
- `python3 scripts/visual-context-inspector-proof.py`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/visual-chat-proof.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

Visual artifact:

- `docs/visual-proofs/checkpoint-84/chat-context-inspector.png`

## Remaining

- Persist retrieval and exposed-schema decisions with each chat turn for
  post-run audit, not only last-request state.
