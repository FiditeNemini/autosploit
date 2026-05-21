# Beta Refresh Checkpoint 34

Date: 2026-05-21

## Scope

- Removed remaining emoji/text-symbol chrome that was generated outside direct view code:
  - tool execution statuses
  - activity feed type markers
  - stash item type markers
  - phase and interaction-mode computed labels
  - localized onboarding navigation arrows
- Changed activity/stash markers to compact text codes so copied exports stay readable and professional.
- Removed phase icons from phase log messages and the phase indicator.

## Files

- `ExploitBot/Sources/ExploitBot/Services/ChatService.swift`
- `ExploitBot/Sources/ExploitBot/Services/ActivityFeed.swift`
- `ExploitBot/Sources/ExploitBot/Services/StashService.swift`
- `ExploitBot/Sources/ExploitBot/Services/Localizer.swift`
- `ExploitBot/Sources/ExploitBot/Models/AppState.swift`
- `ExploitBot/Sources/ExploitBot/Models/Op.swift`
- `ExploitBot/Sources/ExploitBot/Models/PentestPhase.swift`
- `ExploitBot/Sources/ExploitBot/Views/ActivityFeedView.swift`
- `ExploitBot/Sources/ExploitBot/Views/PhaseIndicatorView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/StashTabView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`
- `rg -n "📎|🤖|⏹|📦|🔧|✕|✓|✗|⚡|🔍|📄|⬇|📊|▶|▼|🔑|🌐|⚠️|💻|→|←" ExploitBot/Sources/ExploitBot`

## Result

- Swift app: build passed
- Engine: `22 passed, 3 warnings`
- Symbol scan has no user-visible hits; remaining matches are source comments only.
