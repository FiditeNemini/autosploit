# Checkpoint 229 - Qwen VL Model Folder Blocking

## Goal

Prevent Qwen VL/multimodal folders from being treated as supported text Qwen
runtime folders before the app has a verified multimodal beta lane.

## Changes

- Strengthened `scripts/model-folder-warning-proof.py` with a `qwen3_vl`
  fixture that must remain blocked and expose `isMultimodal=true`.
- Updated `ModelFolderInspector` to detect Qwen VL/multimodal shape from
  `model_type`, path markers, or vision config fields.
- Updated `/state.modelFolderInfo` to expose `isMultimodal`.
- Updated the system review and app flow inventory docs.

## Proof

- `python3 scripts/model-folder-warning-proof.py`
- `python3 scripts/settings-coverage-proof.py`
- `python3 scripts/runtime-coverage-proof.py`
- `swift build --package-path ExploitBot`
- `git diff --check`

## Notes

The red proof failed because `qwen3_vl` was accepted as supported Qwen. The
green path keeps family detection as `Qwen` while marking the folder
multimodal and unsupported until Qwen multimodal inference has its own verified
cache/parser contract.
