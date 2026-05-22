# Checkpoint 223 - Chat Coverage State Keys

## Goal

Make `/qa/chat-coverage` expose the AppState keys behind chat actions, chat
controls, context-window behavior, QA visual chat state, stash handoff, and feed
visibility proofs.

## Changes

- Strengthened `scripts/chat-coverage-proof.py` to require chat `stateKeys`.
- Updated `GET /qa/chat-coverage` with chat/control/context/visual/stash/feed
  state surfaces.
- Strengthened `scripts/app-qa-matrix-smoke-proof.py` so the top-level matrix
  catches missing chat state-key accounting.
- Updated `scripts/coverage-index-proof.py` and `/qa/coverage-index` group
  metadata so chat/context state-key accounting includes the chat keys.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/chat-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `/qa/chat-coverage` listed routes, contracts,
visual manifests, and proofs but did not expose the state keys those proofs
validate. The green path adds that state-key contract and rolls it up through
the coverage index.
