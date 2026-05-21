# Beta Refresh Checkpoint 25 — 2026-05-21

## Scope

Twenty-fifth checkpoint toward the beta-refresh objective:

- Align the Swift Settings UI with the newer engine generation metadata.
- Make chat-template/default-thinking state visible from the app.

## Changes

- Extended `EngineEffectiveConfig` parsing to read:
  - `generation.chat_template_kwargs`;
  - `generation.custom_chat_template`.
- Added a `Template` item to the Settings `Effective Runtime` summary.
- The summary now reports whether the engine is using the model template or a
  custom template, plus the active chat-template kwargs keys when present.

## Evidence

Passed:

```sh
swift build --package-path ExploitBot
git diff --check
```

## Remaining Proof Gap

This checkpoint proves Swift parsing and build integration only. A live
loaded-engine screenshot showing `Template` populated requires the engine to be
started against a model and was not run while the external vMLX process remains
active.
