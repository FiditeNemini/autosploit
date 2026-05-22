# Checkpoint 172 - Stash Add Sheet State

## Goal

Make the Stash Add sheet lifecycle AppState-owned and proofable, so context
catalogue inputs are not hidden behind local-only modal state.

## Changes

- Added `scripts/stash-add-sheet-proof.py`.
- Added AppState-owned Stash Add sheet visibility.
- Added `/qa/stash-add-sheet` with `open`, `cancel`, and `add` actions.
- Extended `/state.stashActions` with `addSheetVisible`.
- Routed the Stash tab `+ Add`, Cancel, sheet dismissal, and sheet submit
  through AppState.
- Kept draft label/content text local to the sheet, while submit still uses the
  existing `recordStashAdd` path.

## Proof

```bash
python3 scripts/stash-add-sheet-proof.py
python3 scripts/stash-actions-proof.py
python3 scripts/stash-retrieval-proof.py
python3 scripts/stash-row-context-actions-proof.py
python3 scripts/stash-send-chat-control-proof.py
```

## Notes

This closes the visible Stash Add modal control gap. Stash item creation,
retrieval, copy, row context actions, send-to-chat, and deletion remain covered
by the existing Stash proofs.
