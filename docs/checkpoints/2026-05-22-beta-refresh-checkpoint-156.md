# Checkpoint 156 - Inference Log Copy

## Scope

- Route Settings and Chat inference-log copy actions through AppState instead of
  writing to the pasteboard directly from the view.

## Changes

- Added `clipboardPreview` to `/state.inferenceLogActions`.
- Added `copyInferenceLog()` in AppState.
- Routed `InferenceLogView` Copy through callbacks supplied by Settings and
  Chat panel owners.
- Extended `scripts/inference-log-actions-proof.py` to prove copy and clear.

## Verification

- `python3 scripts/inference-log-actions-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

- The proof verifies copy action state, copied preview content, clear action
  state, zeroed log length, and activity-feed visibility.
