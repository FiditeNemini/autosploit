# Checkpoint 152 - Sidebar Create Stops Generation

## Scope

- Move the sidebar plus button's stop-before-create behavior into AppState and
  prove it through deterministic state.

## Changes

- `createSidebarOp` now stops active chat generation through
  `stopChatGeneration()` before creating the new operation.
- Removed the sidebar view's direct `chatService.stop()` call.
- Added `stoppedGeneration` to `/state.sidebarActions`.
- Added deterministic QA route `/qa/seed-sidebar-running-create`.
- Added `scripts/sidebar-create-stops-proof.py`.

## Verification

- `python3 scripts/sidebar-create-stops-proof.py`
- `python3 scripts/sidebar-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies the seeded working chat is stopped, `/state.chatControlActions`
  records `stop`, and sidebar create exposes `stoppedGeneration: true`.
