# Beta Refresh Checkpoint 35

Date: 2026-05-21

## Scope

- Replaced tab toolbar text glyph buttons with SF Symbols.
- Removed the Command-key glyph from the visible terminal tooltip to keep the toolbar copy plain and professional.
- Kept the toolbar button dimensions stable at `28x28`.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Tabs/TabBarView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `git diff --check`
- `rg -n "Text\\(icon\\)|let icon: String|ToolbarButton\\(icon:|⌨|⚙" ExploitBot/Sources/ExploitBot/Views/Tabs/TabBarView.swift ExploitBot/Sources/ExploitBot`

## Result

- Swift app: build passed
- Toolbar glyph scan: no hits
