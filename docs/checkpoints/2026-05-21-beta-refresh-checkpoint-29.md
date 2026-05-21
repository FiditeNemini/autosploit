# Beta Refresh Checkpoint 29

Date: 2026-05-21

## Scope

- Replaced native picker controls in the network, report, post-exploitation, and credentials tabs with the shared dark segmented selector.
- Preserved all existing selected values used by scan/report/command generation.
- Reduced remaining native picker surface to the chat deployment selector and CVE settings severity selector.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Tabs/NetworkTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/ReportTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/PostExploitTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/CredsTabView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `git diff --check`
- `rg -n "Picker\\(" ExploitBot/Sources/ExploitBot/Views/Tabs/NetworkTabView.swift ExploitBot/Sources/ExploitBot/Views/Tabs/ReportTabView.swift ExploitBot/Sources/ExploitBot/Views/Tabs/PostExploitTabView.swift ExploitBot/Sources/ExploitBot/Views/Tabs/CredsTabView.swift`

## Notes

- Source and build verification passed.
- Visual QA for these tab bars should be folded into the next broad app screenshot pass.
