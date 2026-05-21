# Checkpoint 50 - Model Folder Runtime Defaults

## Summary

Removed the small/medium/large model-profile lane from the Swift app. Users now
select a model folder, and the app/engine path treats that folder as the source
of truth for model family, JANG/JANGTQ metadata, generation defaults, parser
autodetect, and cache topology.

## Changes

- Added `ModelFolderInspector` to detect Qwen/MiniMax support, `model_type`, and
  the presence of `config.json`, `jang_config.json`, `jangtq_config.json`,
  `generation_config.json`, and tokenizer config files.
- Removed `ModelProfile`, `modelProfile`, `maxToolCount`, and model-profile
  prompt hints from the Swift app.
- Removed curated S/M/L model download cards from the settings model selector.
- Removed hidden Settings writes for temperature, top-p, and max-token app
  overrides so the model folder remains the active generation source.
- Updated Settings to show runtime autodetect instead of profile/parser/KV
  override grids.
- Updated Onboarding to require a selected local Qwen or MiniMax JANG/JANGTQ
  model folder and warn on unsupported folders.
- Forced main app settings to use:
  - generation config from the selected model folder
  - reasoning parser `auto`
  - tool parser `auto`
  - TurboQuant Q4 KV cache encode/decode mode
  - prefix cache enabled
  - prompt L2 disk cache enabled
  - paged cache enabled
  - block L2 disk cache enabled
- Kept user tuning for cache memory percent, L2 disk budgets, paged block size,
  and max autonomous iterations.
- Added `docs/app-flow-inventory-2026-05-21.md` with current tab, chat stream,
  session, context, catalogue, settings, and proof-gate wiring.

## Notes

Only Qwen and MiniMax model families are supported in this beta runtime lane.
The app now warns instead of pretending an unknown folder can be safely inferred
from size labels.

Dynamic catalogue/embedding retrieval is documented as the next context lane.
The current app still sends a static tool catalogue to the model; the documented
target is a structured catalogue that the model can inspect and request from
without force-feeding every item into every prompt.

Tool-action visuals are also documented as a required next UI lane: every tool
call should surface running/progress/error/complete state on its originating tab
button or status row, not only in chat and the global activity feed.

## Verification

Run after this checkpoint:

```bash
swift build --package-path ExploitBot
cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q
git diff --check
rg -n "ModelProfile|modelProfile|maxToolCount|modelProfileHint|curatedModels|\\.tier|tier:" ExploitBot/Sources/ExploitBot -g '*.swift'
```

Visual QA should cover Onboarding model selection and Settings model/runtime
sections, confirming that no S/M/L model profile selector remains and that the
unsupported-folder warning is visible.
