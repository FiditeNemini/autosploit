# Beta Refresh Checkpoint 129 - Mode Selection Flow

## Changed

- Added `scripts/mode-selection-flow-proof.py` to cover onboarding and Sidebar
  mode selection surfaces, not just chat-loop mode behavior.
- Added `/state.modeSelection` with:
  - available mode IDs and labels;
  - current selected mode and active op mode;
  - selection source and last action;
  - onboarding visibility;
  - pending approval visibility/rejection status.
- Added QA routes:
  - `/qa/onboarding-complete`
  - `/qa/seed-pending-approval`
  - `/qa/sidebar-mode`
- Moved onboarding completion into `AppState.completeOnboarding(...)` so the
  view and QA proof share language/model/op/mode setup.
- Moved Sidebar mode switching into `AppState.selectInteractionMode(...)` so
  UI mode selection, active-op persistence, activity logging, and pending
  approval rejection share one path.

## Proof

- `python3 scripts/mode-selection-flow-proof.py`
- `python3 scripts/persistence-proof.py`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The first `live-turn-harness.py` run timed out waiting for the late
`search_context` result; an immediate rerun passed without code changes. The
mode-selection change is therefore verified against the green rerun plus the
focused mode-selection proof and persistence proof.
