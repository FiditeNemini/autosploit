# Beta Refresh Checkpoint 16 — 2026-05-21

## Scope

Sixteenth checkpoint toward the beta-refresh objective:

- Capture a current-build Settings visual proof after the model-default and
  top-p controls landed.
- Verify the proof path without keeping temporary onboarding data in the
  normal app database.

## Visual Evidence

- Built the current Swift package product with `swift build --package-path
  ExploitBot`.
- Wrapped the current debug executable in a temporary QA app bundle at
  `/tmp/ExploitBotQA.app` so macOS launched the current source instead of an
  older bundled app with the same production app name.
- Captured `/tmp/exploitbot-settings-current.png`.
- The screenshot shows:
  - Settings opened on the polished dark squared theme.
  - `Model Defaults` visible in the Inference section.
  - `Temperature`, `Top P`, and `Max Tokens` visible below it.
  - App-level override controls disabled while model defaults are enabled.

## Data Safety

- Temporarily moved the existing `~/.exploitbot` folder aside before creating
  the QA onboarding state.
- Restored the original folder immediately after capture.
- Verified the restored database has no persisted settings and no ops:

```sh
sqlite3 /Users/eric/.exploitbot/data/exploitbot.db 'select key,value from settings order by key;'
sqlite3 /Users/eric/.exploitbot/data/exploitbot.db 'select count(*) from ops;'
```

The settings query returned no rows, and the ops count returned `0`.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
git status --short
```

The repo was clean before this documentation checkpoint.
