# Checkpoint 86 - Request Context Audit Persistence

## Scope

- Preserve the dynamic context/tool-schema decision for each assistant turn, not
  only as the latest ephemeral request state.

## Changes

- `ChatMessage` now carries request audit metadata:
  `contextSummary`, `contextSnippetCount`, and `toolSchemaNames`.
- `ChatService.streamCompletion()` attaches the bounded context packet and
  selected tool schema names to the assistant placeholder for the request.
- Message persistence migration `v5-message-request-audit` adds request-audit
  columns to `messages`.
- `saveCurrentMessages()` and `loadMessages(for:)` persist and restore audit
  metadata.
- `/messages` exposes context/tool audit fields for proof and UI inspection.
- Added QA route `/qa/save-current-messages`.
- Added `scripts/request-audit-proof.py`.

## Proof

- `python3 scripts/request-audit-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/persistence-proof.py`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Remaining

- Build a richer UI history view for prior request-audit records instead of
  exposing only the current inspector plus API proof.
- Real-engine cache metrics screenshot proof.
