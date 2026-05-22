# Checkpoint 298 - Qwen Multimodal Start Block Proof

## Goal
Make the current Qwen multimodal/VL runtime gap enforceable with a dedicated
engine-start proof.

## Changes
- Added `scripts/qwen-multimodal-start-proof.py`.
- Added the proof to the `qwenMultimodalRuntime` gap contract.
- Added the proof to runtime/cache coverage.
- Updated the app flow inventory and system review docs.

## Proof
- `python3 scripts/qwen-multimodal-start-proof.py`
- `python3 scripts/gap-ledger-proof.py`
- `python3 scripts/runtime-coverage-proof.py`

## Notes
The red gap-ledger proof failed because the Qwen multimodal gap only named the
folder-warning and generic unsupported-family start-block proofs. The green path
adds a Qwen VL/JANGTQ fixture that stays `family=Qwen`, exposes
`isMultimodal=true`, remains unsupported, leaves the engine stopped, sets
`healthStatus=blocked`, and reports the multimodal-not-yet-supported boundary.
