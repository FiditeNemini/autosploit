# Beta Refresh Checkpoint 18 — 2026-05-21

## Scope

Eighteenth checkpoint toward the beta-refresh objective:

- Improve Settings row layout at the app minimum size.
- Preserve selectable Settings labels while keeping controls aligned.

## Changes

- Updated `SettingRow` to use a stable label column.
- Let row labels wrap to two lines instead of compressing horizontally.
- Gave right-side controls a minimum content width and layout priority.
- Enabled explicit text selection on row labels in addition to the existing
  Settings-level text selection.

## Visual Evidence

Captured a current-source QA screenshot at an app window size of `1280x760`:

- `/tmp/exploitbot-settings-min-layout.png`

The screenshot shows the Settings sheet at the minimum-size window. The top
sections remain aligned, the model rows keep their button/metadata alignment,
and the Inference row begins with the `Model Defaults` label and dark switch
without horizontal label/control overlap.

## Data Safety

- Used the same temporary QA onboarding flow as prior visual checks.
- Restored the original `~/.exploitbot` folder immediately after capture.
- Verified the restored database still has `0` ops.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
```
