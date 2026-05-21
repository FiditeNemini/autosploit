# Beta Refresh Checkpoint 39

Date: 2026-05-21

## Scope

- Added `script/build_and_run.sh` for repeatable SwiftPM macOS app bundle builds and foreground launches.
- Added `.codex/environments/environment.toml` so Codex can run the app through the project script.
- Darkened and squared the onboarding first-run surface by replacing circular step badges, flag emoji cards, and the bright filled Continue button.
- Replaced language flags with compact text badges so first launch matches the professional Graphite Ops direction.

## Files

- `script/build_and_run.sh`
- `.codex/environments/environment.toml`
- `ExploitBot/Sources/ExploitBot/Views/Onboarding/OnboardingView.swift`

## Verification

- `./script/build_and_run.sh --verify`
- Visual inspection with Computer Use against `dist/ExploitBot.app`

## Result

- Swift app bundle build and launch passed.
- Visual QA confirmed the first-run language screen is dark, squared, and free of flag emoji/bright filled controls.

## Notes

- The script stages a local `dist/ExploitBot.app`; `dist/` is already ignored.
- This checkpoint does not change onboarding behavior or persistence.
