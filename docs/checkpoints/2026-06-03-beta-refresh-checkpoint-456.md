# Checkpoint 456 - Session Cache MiniMax Batching Mirror

## Goal

Make `/qa/session-context-cache-flow` explicitly reflect the required MiniMax
live batching artifact instead of relying only on the aggregate continuous
batching contract.

## Changes

- Added `minimaxLiveContinuousBatchingArtifact` to the
  `/qa/session-context-cache-flow` contract map.
- Added MiniMax live batching counters to the session/cache route:
  `minimaxContinuousBatchingMaxRunningObserved` and
  `minimaxContinuousBatchingRequestsProcessed`.
- Updated the objective runtime session/parallel/batching evidence summary to
  name both Qwen and MiniMax live batching proofs.
- Tightened `scripts/session-context-cache-flow-proof.py` so the route fails if
  the MiniMax live batching counter is missing.

## Proof

Verified:

```bash
python3 scripts/session-context-cache-flow-proof.py
```

The route now mirrors:

- `continuousBatchingProofLevel=source-and-live-qwen-minimax-plus-qwen-4way-stress-backed`
- `minimaxContinuousBatchingMaxRunningObserved=2`
- `minimaxContinuousBatchingRequestsProcessed=2`
- `qwenHighCardinalityContinuousBatchingMaxRunningObserved=4`

## Remaining

- Superseded by Checkpoint 458 for live loaded-model agent stress.
