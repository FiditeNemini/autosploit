# Beta Refresh Checkpoint 11 — 2026-05-21

## Scope

Eleventh checkpoint toward the beta-refresh objective:

- Tighten the dark Graphite Ops UI pass after screenshot review.
- Remove remaining explicit white foreground usage from Swift UI sources.
- Make visible cards, bubbles, overlays, and modals less rounded.
- Lock the SwiftUI window to its content minimum size.
- Keep the chat resize handle consistent with the actual chat panel minimum.

## Changes

- Added `.windowResizability(.contentMinSize)` to the app scene.
- Raised the chat panel drag minimum from `280` to `360` to match the panel
  frame minimum.
- Replaced explicit `.white` foregrounds under `ExploitBot/Sources/ExploitBot`
  with semantic theme colors.
- Changed onboarding selected/active indicators from white to `accentBlue`.
- Reduced visible rounded rectangles from 10-16px to 8px across onboarding,
  chat bubbles, reasoning blocks, settings status, network/web cards, and the
  finding wizard container.

## Visual Evidence

Captured the SwiftPM debug app after relaunch:

```text
/tmp/exploitbot-debug-onboarding-front.png
```

Observed result:

- Dark onboarding surface with no white selected ring.
- Active step and selected language use accent blue.
- Language cards are squared to the 8px theme radius.
- The app window is large enough to preserve the onboarding bottom action bar
  without compressing the primary content.

The screenshot still includes background desktop/app windows because it is a
full-screen `screencapture`, but the frontmost ExploitBot debug window is the
patched SwiftPM build.

## Evidence

Passed source sweep:

```sh
rg -n "Color\\.white|foregroundColor\\(\\.white\\)|foregroundColor\\(Color\\.white\\)|cornerRadius: 1[0-9]|cornerRadius\\(1[0-9]" ExploitBot/Sources/ExploitBot -g '*.swift'
```

No matches.

Full verification is rerun after this checkpoint before committing.
