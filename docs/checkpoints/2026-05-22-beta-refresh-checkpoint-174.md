# Checkpoint 174 - Model Folder Picker State

## Goal

Make model-folder selection observable and proofable from AppState, with selected
folders inspected for config files instead of relying on small/medium/large
profile guesses.

## Changes

- Added `scripts/model-folder-picker-proof.py`.
- Added AppState-owned model folder picker state:
  - open
  - cancel
  - select
  - selected path
  - supported family
  - support message
  - detected config summary
- Added `/qa/model-folder-picker` for deterministic picker lifecycle proof.
- Routed Settings Browse and downloaded-model selection through
  `AppState.selectModelFolder`.
- Extended `ModelFolderInspector` and `/state.modelFolderInfo` with
  `jangtq_config.json` detection.
- Kept the existing Qwen/MiniMax support warning and unsupported-start blocking
  behavior.

## Proof

```bash
python3 scripts/model-folder-picker-proof.py
python3 scripts/model-folder-warning-proof.py
python3 scripts/unsupported-model-start-proof.py
python3 scripts/settings-category-coverage-proof.py
```

## Notes

The model page now proves folder selection as a first-class state transition.
The selected folder exposes `config.json`, `jang_config.json`,
`jangtq_config.json`, `generation_config.json`, and tokenizer config detection
through the app state surface used by QA scripts.
