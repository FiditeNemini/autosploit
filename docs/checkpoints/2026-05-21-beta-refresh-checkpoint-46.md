# Beta Refresh Checkpoint 46

Date: 2026-05-21

## Scope

- Darkened remaining bright primary action controls on main UI, modal, and settings-adjacent surfaces.
- Replaced white-filled send/finding/deploy/stash/scan/search/approve actions with dark bordered controls.
- Added darker sheet presentation backgrounds and stronger minimum sizing for deploy-agent, add-stash, and rename-op sheets.
- Removed the remaining emoji label from the CVE full-sync action.
- Visually checked onboarding, the main window, and Settings after launching the app through the repo run script.

## Files

- `ExploitBot/Sources/ExploitBot/Views/Chat/ChatPanelView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Findings/FindingWizardView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Settings/CVESettingsView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Sidebar/SidebarView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/OSINTTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/ReportTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/StashTabView.swift`
- `ExploitBot/Sources/ExploitBot/Views/Tabs/WebTabView.swift`
- `docs/engine-migration-prep-2026-05-21.md`

## Verification

- `swift build --package-path ExploitBot`
- `./script/build_and_run.sh --verify`
- `PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`
- Computer Use visual QA of onboarding, main app, and Settings.

## Result

- Swift app: build passed.
- Engine: `31 passed, 3 warnings`.
- Whitespace gate passed.
- App launch verification passed.
- Visual QA confirmed dark onboarding, main app, and Settings surfaces after the control updates.

## Notes

- System alerts and native file panels still use system chrome. The custom app surfaces checked here are dark and selectable.
