# Beta Refresh Checkpoint 402

## Goal

Expose the real Qwen hybrid SSM rederive proof through runtime coverage instead
of leaving it only inside the checked-in live JSON artifact.

## Changes

- Added `ssmReDerive` to `/qa/runtime-coverage.liveProofs.qwen`.
- Added `qwenSSMReDeriveArtifact`, `qwenSSMReDeriveArtifactOK`,
  `qwenSSMReDeriveRequested`, `qwenSSMReDeriveCompleted`,
  `qwenSSMReDeriveNoFailures`, and `qwenSSMReDeriveLastNumTokens` to
  `/qa/runtime-coverage`.
- Mirrored the same Qwen SSM rederive fields through
  `/qa/coverage-index.groups.runtimeAndCache`.
- Strengthened runtime, coverage-index, and broad app QA matrix proofs so the
  real checkpoint-112 artifact must show requested/completed/no-failure SSM
  rederive semantics.
- Updated the system review and flow inventory to note that real-model async
  rederive execution is now machine-auditable from the app surface.

## Proof

- `python3 scripts/runtime-coverage-proof.py`
- `python3 scripts/coverage-index-proof.py`
- `python3 scripts/app-qa-matrix-smoke-proof.py`

## Notes

The red runtime proof failed because `/qa/runtime-coverage` only exposed coarse
`ssmCompanionL2=true` for Qwen. The green path reads
`docs/live-proofs/checkpoint-112-qwen-hybrid-block-l2-ssm-restart-replay-live.json`
and surfaces the real requested/completed/no-failures SSM rederive checks plus
the token count.
