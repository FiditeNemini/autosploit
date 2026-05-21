# Beta Refresh Checkpoint 27 — 2026-05-21

## Scope

Twenty-seventh checkpoint toward the beta-refresh objective:

- Remove another visible native popup control from the main app surface.
- Keep Activity Feed controls dark, squared, selectable, and copyable.

## Changes

- Added `DarkSegmentedControl`, a compact dark segmented selector using the
  shared `DarkOption` model.
- Replaced the Activity Feed verbosity picker with the dark segmented selector.
- Option labels have copy context menus and stay inside fixed minimum-width
  segments to prevent header squeeze.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
git diff --check
rg -n "Picker\\(" ExploitBot/Sources/ExploitBot/Views/ActivityFeedView.swift ExploitBot/Sources/ExploitBot/Views/Settings/SettingsView.swift
```

The `rg` command returned no picker hits for Settings or Activity Feed.

Visual proof captured from a temporary isolated QA app:

- `/tmp/exploitbot-activity-dark-segmented.png`

## Notes

The QA run temporarily moved `~/.exploitbot` aside, launched a scratch app,
captured the screenshot, and restored the original `~/.exploitbot` directory.
The external `/Applications/vMLX.app` process was not stopped or modified.

## Remaining Proof Gap

Other native pickers still exist in lower-priority sheets/tabs such as finding
creation, CVE custom severity, deploy-agent type, and some tool tabs. They are
still visible in source scan output and need follow-up replacement before the
entire app can be called free of native popup styling.
