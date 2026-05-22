# Checkpoint 157 - Web Header Copy

## Scope

- Route the Web tab header Copy button through AppState instead of using the
  `CopyButton` pasteboard fallback directly.

## Changes

- Added `recordWebCopyAll()` in AppState.
- Added `/qa/web-copy-all` for deterministic proof of the header copy action.
- Added `onCopyAll` to `WebTabView` and wired it from `ContentView`.
- Added `scripts/web-header-copy-proof.py`.

## Verification

- `python3 scripts/web-header-copy-proof.py`
- `python3 scripts/web-direct-actions-proof.py`
- `python3 scripts/web-row-context-actions-proof.py`
- `python3 scripts/tool-action-chat-control-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies `/state.webDirectActions`, clipboard preview, and Web tab
  activity for the header copy path.
