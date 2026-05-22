# Checkpoint 140 - Stash Row Context Actions

## Scope

- Make Stash row context-menu copy actions observable through the same AppState
  action state as visible Stash row controls.

## Changes

- Added `/qa/stash-row-action` with deterministic `contextCopyContent` and
  `contextCopyLabel` actions.
- Routed Stash row context-menu Copy Content and Copy Label through the
  existing Stash copy callback path.
- Added `scripts/stash-row-context-actions-proof.py`.

## Verification

- `python3 scripts/stash-row-context-actions-proof.py`
- `python3 scripts/stash-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies clipboard preview, last item id, distinct action name, and
  Stash tab activity for both context-menu content and label copies.
