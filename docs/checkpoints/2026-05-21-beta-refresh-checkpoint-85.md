# Checkpoint 85 - Persistence Rebuild Proof

## Scope

- Prove settings, per-operation messages, and parsed tab results survive an app
  relaunch instead of relying on live tool output only.

## Changes

- Added `scripts/persistence-proof.py`.
- Added QA route `/qa/seed-persistence-fixture` to seed an isolated persistence
  fixture with context settings, agent settings, chat settings, and a persisted
  `nmap` tool output.
- `AppState.loadMessages(for:)` now rebuilds `ResultsStore` from restored
  tool-call messages, so tabs regain parsed results after switching operations
  or relaunching.
- The persistence proof uses a temporary `HOME`, relaunches the app, and checks
  that the restored `nmap` message reparses into a visible `443/https` port.

## Proof

- `python3 scripts/persistence-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/settings-apply-proof.py`
- `python3 scripts/live-turn-harness.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

## Remaining

- Real-engine cache metrics screenshot proof.
- Persist per-turn context-packet and exposed-tool-schema audit records.
