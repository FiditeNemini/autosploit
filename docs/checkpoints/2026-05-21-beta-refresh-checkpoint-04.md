# Beta Refresh Checkpoint 04 — 2026-05-21

## Scope

Fourth checkpoint toward the beta-refresh objective:

- Read the engine `effective_config` metadata from `/health` in the Swift app.
- Keep the parsed runtime metadata on `EngineManager`.
- Display a compact effective runtime summary in Settings.
- Add manual picker options for the newly imported MiniMax M2 and Gemma4
  reasoning parsers.

## Changed App Surface

- Updated `EngineManager`
  - Adds `EngineEffectiveConfig`.
  - Parses effective model, parser, generation, cache, KV quantization, and L2
    disk cache metadata from `/health`.
  - Clears runtime metadata when the engine stops/restarts.
- Updated `SettingsView`
  - Shows live effective runtime fields when the engine reports them.
  - Adds `minimax_m2` and `gemma4` reasoning parser choices.

## Verification

Passed:

```sh
swift build
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
git diff --check
```

The app build verifies the Swift integration. A visual check against the debug
app is still pending because the local machine also has an installed
`ExploitBot.app` with the same app name/bundle identity.
