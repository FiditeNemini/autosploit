# Beta Refresh Checkpoint 28

Date: 2026-05-21

## Scope

- Replaced the finding creation wizard's native macOS pickers with the shared dark theme controls.
- Removed emoji-styled header chrome from the finding modal and squared the close/footer button backgrounds.
- Preserved the existing stored vulnerability type, severity, and status values for finding persistence/API compatibility.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Findings/FindingWizardView.swift`

## Verification

- `swift build --package-path ExploitBot`
- `git diff --check`
- `rg -n "Picker\\(" ExploitBot/Sources/ExploitBot/Views/Findings/FindingWizardView.swift`

## Notes

- Source and build verification passed.
- No standalone screenshot was captured for this modal checkpoint; opening this sheet reliably from the scratch QA app needs a seeded operation/finding flow and should be handled in a broader visual pass.
