# Beta Refresh Checkpoint 17 — 2026-05-21

## Scope

Seventeenth checkpoint toward the beta-refresh objective:

- Remove bright native switch and slider controls from Settings.
- Darken the remaining filled Settings action buttons.
- Keep first-run onboarding aligned with the same darker control language.

## Changes

- Added shared dark controls in `Theme/Controls.swift`:
  - `DarkSwitchToggleStyle`
  - `DarkSlider`
- Replaced Settings inference/cache/agent toggles with the dark square switch.
- Replaced Settings temperature, top-p, and cache-memory sliders with the dark
  slider.
- Replaced the inference log `Auto-scroll` native switch with the dark switch.
- Replaced the onboarding scope native switch with the dark switch.
- Changed Settings `Done` and `Apply & Restart Engine` from filled blue blocks
  to darker stroked actions.

## Visual Evidence

Captured current-source QA screenshots with a temporary app bundle:

- `/tmp/exploitbot-settings-dark-controls.png`
- `/tmp/exploitbot-settings-dark-controls-v2.png`

The v2 screenshot shows the Settings sheet with dark switches, dark sliders,
and a dark stroked `Done` action.

## Data Safety

- Used a temporary QA onboarding state by moving `~/.exploitbot` aside during
  capture.
- Restored the original `~/.exploitbot` immediately afterward.
- Verified the restored database still has `0` ops.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
rg -n "toggleStyle\\(\\.switch\\)|Slider\\(" ExploitBot/Sources/ExploitBot/Views/Settings ExploitBot/Sources/ExploitBot/Views/Onboarding -g '*.swift'
```

The source check now only reports `DarkSlider` usages in Settings and no native
switch/slider controls in Settings or Onboarding.
