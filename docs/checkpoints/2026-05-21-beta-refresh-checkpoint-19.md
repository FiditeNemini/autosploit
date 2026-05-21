# Beta Refresh Checkpoint 19 — 2026-05-21

## Scope

Nineteenth checkpoint toward the beta-refresh objective:

- Tighten the lower Settings subpanels.
- Reduce remaining bright filled action treatments.
- Improve selectable text coverage in model download, CVE, and tool settings.
- Protect the tool table from horizontal squeezing.

## Changes

- `CVESettingsView`
  - Converted CVE import/add/save buttons from filled accent blocks to darker
    stroked actions.
  - Enabled text selection at the view level and on CVE result rows.
  - Let CVE descriptions and tags wrap to two lines instead of hard truncating.
- `ModelDownloadView`
  - Converted model download/load actions to darker stroked actions.
  - Enabled text selection for model names, descriptions, paths, and status
    text.
  - Let curated model descriptions wrap to two lines.
- `ToolSettingsView`
  - Converted the install-all and per-tool install actions to darker stroked
    actions.
  - Wrapped the tool list in horizontal scrolling with a stable table width so
    path/tool columns do not squeeze at narrow Settings widths.
  - Enabled text selection for the summary, tool rows, path text, and install
    log.

## Visual Evidence

Captured current-source QA screenshots:

- `/tmp/exploitbot-settings-subpanels-top.png`
- `/tmp/exploitbot-settings-subpanels-lower.png`
- `/tmp/exploitbot-settings-subpanels-pagedown.png`
- `/tmp/exploitbot-settings-subpanels-click-pagedown.png`

The automation opened the current QA bundle and verified the top Settings
surface. AppleScript and accessibility scrolling did not move the SwiftUI
overlay scroll position in this run, so lower-subpanel visual proof is still
partial; the patched lower subpanel files are covered by build and source
inspection in this checkpoint.

## Data Safety

- Used the same temporary QA onboarding flow as prior visual checks.
- Restored the original `~/.exploitbot` folder after capture attempts.
- Verified the restored database still has `0` ops.
- Confirmed no `ExploitBotQA` or `ExploitBot` test process remained running.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
rg -n "fill\\(Color\\.accent(Blue|Green|Red|Orange|Amber|Cyan|Purple)|toggleStyle\\(\\.switch\\)|Slider\\(" ExploitBot/Sources/ExploitBot/Views/Settings -g '*.swift'
```

The source scan still shows muted status/background accent fills for banners,
badges, and error/success panels, plus the expected `DarkSlider` calls. It no
longer shows the changed Settings subpanel action buttons as filled accent
blocks.
