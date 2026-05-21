# Beta Refresh Checkpoint 24 — 2026-05-21

## Scope

Twenty-fourth checkpoint toward the beta-refresh objective:

- Remove more native/light Settings controls from the Graphite Ops theme.
- Make Settings selection text visible, selectable, and copyable.
- Keep selection controls stable at the app minimum width.

## Changes

- Added `DarkOption` and `DarkOptionGrid`, a reusable dark option selector with:
  - 4px card radius matching the squared app theme;
  - dark input surfaces instead of native picker/radio styling;
  - selected-state border and checkmark;
  - selectable title/subtitle text;
  - copy context menu for option labels;
  - adaptive minimum item widths to prevent row squeeze.
- Replaced Settings native pickers/radio controls for:
  - model profile;
  - reasoning parser;
  - tool-call parser;
  - KV cache quantization;
  - max concurrent agents.
- Removed emoji-heavy parser labels from these Settings controls in favor of
  cleaner professional labels and short copyable descriptions.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
git diff --check
```

Visual proof captured from a temporary isolated QA app:

- `/tmp/exploitbot-settings-option-grid-v2.png`

The screenshot shows the Settings surface using dark option cards for Model
Profile with no white native radio/picker control visible in that section.

## Notes

The QA run temporarily moved `~/.exploitbot` aside, launched a scratch app, and
then restored the original `~/.exploitbot` directory after visual capture. The
standing external `/Applications/vMLX.app` process was not stopped or modified.

## Remaining Proof Gap

This checkpoint visually verifies the top Settings selector surface. Lower
parser/cache selector sections compile and use the same component, but a lower
scroll screenshot was not captured because macOS accessibility scrolling did
not move the SwiftUI Settings overlay in this run.
