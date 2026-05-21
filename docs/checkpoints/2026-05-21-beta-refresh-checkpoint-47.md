# Beta Refresh Checkpoint 47

Date: 2026-05-21

## Scope

- Centralized the main resizable panel bounds in `AppState`.
- Raised the chat panel minimum width to prevent the composer, header controls, and message content from squeezing.
- Raised the lower activity/terminal panel minimum height and max height through shared constants.
- Updated `ContentView` to render from clamped panel dimensions and to route drag changes through setter methods.
- Visually checked the main app layout after launching through the repo run script.

## Files

- `ExploitBot/Sources/ExploitBot/Models/AppState.swift`
- `ExploitBot/Sources/ExploitBot/Views/ContentView.swift`
- `docs/engine-migration-prep-2026-05-21.md`

## Verification

- `swift build --package-path ExploitBot`
- `./script/build_and_run.sh --verify`
- `PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`
- Computer Use visual QA of the main app layout.

## Result

- Swift app: build passed.
- Engine: `31 passed, 3 warnings`.
- Whitespace gate passed.
- App launch verification passed.
- Visual QA confirmed the main app layout remains properly positioned after the resize minimum changes.

## Notes

- This checkpoint does not change the main window minimum size. It hardens the nested resizable panels inside that window.
