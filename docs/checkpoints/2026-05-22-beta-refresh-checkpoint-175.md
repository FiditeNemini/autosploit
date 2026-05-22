# Checkpoint 175 - Onboarding Model Picker State

## Goal

Make first-run onboarding use the same observable model-folder selection path as
Settings, so initial setup also proves folder-only selection and config
autodetect.

## Changes

- Added `scripts/onboarding-model-picker-proof.py`.
- Added `/qa/onboarding-model-picker` with `open`, `cancel`, and `select`.
- Extended model folder picker state with a `source` field.
- Routed onboarding Browse through AppState model picker open/cancel/select.
- Routed onboarding completion through `selectModelFolder(..., source:
  "onboarding")` before saving engine config.
- Preserved existing onboarding completion and mode-selection behavior.

## Proof

```bash
python3 scripts/onboarding-model-picker-proof.py
python3 scripts/mode-selection-flow-proof.py
python3 scripts/model-folder-picker-proof.py
python3 scripts/model-folder-warning-proof.py
```

## Notes

The onboarding path now records MiniMax/Qwen support, selected path, detected
JANG/JANGTQ/generation/tokenizer config files, and picker source through the
same state surface used by Settings model-folder QA.
