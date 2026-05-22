# Beta Refresh Checkpoint 167

## Scope

- Prove the chat header inference-log visibility control is wired through
  `AppState`, not hidden in local view-only state.
- Keep clear/copy log actions on the same action-state path so the visible panel
  and settings log panel report consistently.

## Changes

- Added `isInferenceLogVisible` to `AppState`.
- Added `isVisible` to `/state.inferenceLogActions`.
- Wired `ChatPanelView` inference-log visibility through
  `onSetInferenceLogVisible`.
- Extended `/qa/inference-log-action` with `toggleVisible`.
- Extended `scripts/inference-log-actions-proof.py` to assert hidden initial
  state, toggle action state, copy, and clear.

## Proof

- Red proof first:
  `python3 scripts/inference-log-actions-proof.py` failed because
  `/state.inferenceLogActions` did not expose visibility state.
- Green proof:
  `python3 scripts/inference-log-actions-proof.py` passed.
- Build proof:
  `swift build --package-path ExploitBot` passed.

