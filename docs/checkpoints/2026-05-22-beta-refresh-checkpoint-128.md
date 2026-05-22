# Beta Refresh Checkpoint 128 - Stash Action State

## Changed

- Added `scripts/stash-actions-proof.py` to cover Stash add/copy/send/delete
  behavior through the app TestServer.
- Added `/state.stashActions` with:
  - Add, Copy All, Copy, Send, and Delete labels;
  - current stash item rows;
  - clipboard preview;
  - last action plus last item/deleted IDs.
- Added QA routes for seeded Stash actions:
  - `/qa/seed-stash-actions`
  - `/qa/stash-add`
  - `/qa/stash-copy-all`
  - `/qa/stash-copy`
  - `/qa/stash-send`
  - `/qa/stash-delete`
- Routed Stash tab Add, Copy All, per-row Copy, Send, and Delete buttons through
  AppState action handlers so visible button usage and proof routes share the
  same state/update path.
- Extended `CopyButton` with an optional copy callback while preserving the
  default direct clipboard behavior for existing call sites.

## Proof

- `python3 scripts/stash-actions-proof.py`
- `python3 scripts/stash-retrieval-proof.py`
- `python3 scripts/context-catalog-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

This closes the direct Stash button/action-state gap. Existing retrieval and
context-catalog behavior remain covered by their adjacent proofs.
