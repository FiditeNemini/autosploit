# Beta Refresh Checkpoint 30

Date: 2026-05-21

## Scope

- Replaced the chat deploy-agent type menu with the shared dark option grid.
- Replaced the custom CVE severity picker with the shared dark segmented selector.
- Cleared the current native `Picker` usage scan under `ExploitBot/Sources/ExploitBot/Views`.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Chat/ChatPanelView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/CVESettingsView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `git diff --check`
- `rg -n "Picker\\(" ExploitBot/Sources/ExploitBot/Views`

## Notes

- Source and build verification passed.
- This does not mean every native AppKit/SwiftUI control is gone; it specifically clears the visible picker/menu controls found by the source scan.
