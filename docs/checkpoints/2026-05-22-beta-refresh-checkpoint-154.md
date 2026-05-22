# Checkpoint 154 - Tool Action Chat Control

## Scope

- Route AppState tool-action prompt queues through the same chat-control send
  path used by visible chat and stash sends.

## Changes

- Replaced direct `chatService.send(...)` calls in AppState prompt-queueing
  helpers with `sendChatMessage(...)` for Web verify/search-related, Report
  agent draft, Recon action, Network protocol action, Creds crack action, and
  Exploit action.
- Added `scripts/tool-action-chat-control-proof.py`.

## Verification

- `python3 scripts/tool-action-chat-control-proof.py`
- `python3 scripts/web-row-context-actions-proof.py`
- `python3 scripts/web-verify-action-proof.py`
- `python3 scripts/report-agent-action-proof.py`
- `python3 scripts/recon-action-status-proof.py`
- `python3 scripts/network-protocol-action-proof.py`
- `python3 scripts/creds-action-results-proof.py`
- `python3 scripts/exploit-action-differentiation-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The first attempted adjacent proof batch was invalid because multiple
  app-owning scripts raced on the same app process and port. The affected
  proofs were rerun serially.
