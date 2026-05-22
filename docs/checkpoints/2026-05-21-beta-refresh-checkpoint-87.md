# Checkpoint 87 - Request Audit Badges

## Scope

- Make per-turn context/tool-schema audit decisions visible on the assistant
  message that used them.

## Changes

- Added `RequestAuditBadgeRow` below assistant bubbles when a message has
  request-audit metadata.
- Assistant audit badges show selected context count and exposed tool-schema
  count with hover details.
- Added QA route `/qa/seed-chat-request-audit-visual`.
- Added `scripts/visual-request-audit-proof.py`.

## Proof

- `python3 scripts/visual-request-audit-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/request-audit-proof.py`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

Visual artifact:

- `docs/visual-proofs/checkpoint-87/chat-request-audit-badges.png`

## Remaining

- Real-engine cache metrics screenshot proof.
- A full request-audit history browser/filter view.
