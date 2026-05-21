# Beta Refresh Checkpoint 01 — 2026-05-21

## Scope

First checkpoint toward the beta-refresh objective:

- Darken the chosen Graphite Ops visual direction.
- Apply the new dark graphite palette to the Swift app.
- Raise core window and pane minimum sizes.
- Enable root-level text selection.
- Add first launch-side model-folder default loading for generation config and parser defaults.

## UI Changes

- `Colors.swift` now uses a dark graphite palette instead of the older black/purple-blue contrast.
- Main window minimum is now `1280x760`; default is `1440x920`.
- Sidebar width increased to `236`.
- Chat panel minimum width is now `360`.
- Bottom activity feed minimum height is now `140`; terminal minimum height is now `160`.
- Root `ContentView` enables text selection for normal SwiftUI text descendants.
- Primary controls that previously used a near-white fill now use restrained accent fills.
- `theme-preview-02-graphite-ops.html` was darkened so the preview no longer uses a white main canvas.

## Engine Changes

- `launch.py` now reads model-folder defaults from:
  - `generation_config.json`
  - `jang_config.json`
- `generation_config.json` can supply startup defaults for:
  - `temperature`
  - `top_p`
  - `max_new_tokens` / `max_tokens` / `max_output_tokens`
- `jang_config.json` capabilities can supply parser defaults for:
  - `reasoning_parser`
  - `tool_parser` / `tool_call_parser`
- Explicit CLI/app values still override model-folder defaults.

This is launch-side support only. Full server/API health exposure and deeper vMLX parser/cache migration remain open.

## Verification

Passed:

```sh
swift build
python3 -m compileall -q ExploitBotEngine
PYTHONPATH=ExploitBotEngine python3 -m unittest discover -s ExploitBotEngine/testsuite -v
```

Visual checkpoint caveat:

- A debug `swift run ExploitBot` binary launched successfully.
- Computer Use selected the installed release app with the same bundle id instead of the debug process, so this checkpoint does not claim a debug-app screenshot proof yet.
