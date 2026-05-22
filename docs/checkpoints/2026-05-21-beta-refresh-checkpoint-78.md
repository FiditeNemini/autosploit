# Checkpoint 78 - New Context Cache Topology Proof

## Scope

- Tighten the new-context proof around long-context cache behavior.
- Confirm a fresh chat/context window does not disable the required cache stack.
- Expose token counters through the QA state route so reset behavior is
  script-verifiable.

## Changes

- Added prompt, completion, and cached token counters to the QA `/state`
  metrics payload.
- Strengthened `scripts/live-turn-harness.py` so `/context/new` must leave all
  required engine defaults intact:
  - prefix cache;
  - prompt L2 disk cache;
  - paged cache;
  - block L2 disk cache;
  - TurboQuant Q4 KV cache;
  - model-folder generation defaults.
- The harness also verifies the visible chat is cleared and prompt,
  completion, and cached token counters reset to zero.

## Proof

- `python3 scripts/live-turn-harness.py`

The proof passed after the QA state payload exposed the token counters.

## Remaining

- This proves app session reset semantics with the mock engine. A real-model
  cross-run cache hit remains separate from the new-context UI behavior.
