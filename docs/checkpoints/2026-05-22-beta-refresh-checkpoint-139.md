# Checkpoint 139 - Web Row Context Actions

## Scope

- Make Web vulnerability card context-menu copy and stash actions observable
  through AppState and QA proof routes.

## Changes

- Added `/qa/web-row-action` for deterministic Web row context actions.
- Routed Web row context-menu copy-title, copy-target, and copy-details actions
  through AppState and `/state.webDirectActions`.
- Context-menu Stash now uses the same Web/Stash action path as the visible row
  Stash button, so `/state.stashActions` records the created item.
- Web copied/stashed detail text now includes the CVE line when present.
- Added `scripts/web-row-context-actions-proof.py`.

## Verification

- `python3 scripts/web-row-context-actions-proof.py`
- `python3 scripts/web-direct-actions-proof.py`
- `python3 scripts/stash-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof covers title copy, target copy, full details copy, and context-menu
  stash for the seeded Apache CVE finding.
