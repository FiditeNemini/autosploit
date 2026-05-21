# Beta Refresh Checkpoint 31

Date: 2026-05-21

## Scope

- Removed emoji-heavy action labels and empty-state marks from the main SwiftUI views.
- Replaced close/delete/status symbols with SF Symbols or plain text where appropriate.
- Normalized tab action buttons to direct labels like `Scan`, `Search`, `Generate`, and `Stash`.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Chat/ChatPanelView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Onboarding/OnboardingView.swift`
- `ExploitBot/Sources/ExploitBot/Views/PhaseIndicatorView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/CVESettingsView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/ModelDownloadView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/CredsTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/ExploitTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/NetworkTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/OSINTTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/PostExploitTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/ReconTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/ReportTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/StashTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/WebTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Terminal/TerminalPanelView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `git diff --check`
- `rg -n "📎|🤖|⏹|📦|🔧|✕|✓|✗|⚡|🔍|📄|⬇|📊|▶|▼|🔑|🌐|⚠️|💻|→|←" ExploitBot/Sources/ExploitBot/Views`

## Notes

- Source and build verification passed.
- This pass intentionally targeted visible emoji/text-symbol chrome in `Views`; icon-only SF Symbol usage remains where it matches the professional theme direction.
