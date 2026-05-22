# Checkpoint 150 - Window Overlay Actions

## Scope

- Route app-shell terminal, settings, and finding-wizard overlay controls
  through AppState and expose deterministic action state.

## Changes

- Added `WindowOverlayActionState` and exposed it as
  `/state.windowOverlayActions`.
- Added deterministic QA routes `/qa/seed-window-overlay-actions` and
  `/qa/window-overlay-action`.
- Routed top-bar terminal/settings buttons, terminal close, settings close, and
  finding-wizard dismiss controls through AppState callbacks.
- Added `scripts/window-overlay-actions-proof.py`.

## Verification

- `python3 scripts/window-overlay-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies terminal visibility, settings visibility, finding-wizard
  visibility, and activity-feed state for every overlay action.
