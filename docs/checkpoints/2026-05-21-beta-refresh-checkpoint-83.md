# Checkpoint 83 - Semantic CVE Embedder Proof

## Scope

- Prove semantic CVE context mode actually invokes the embedder path when stored
  embeddings are available.
- Avoid mistaking text-search fallback for semantic ranking.

## Changes

- `CVEService` now honors `EXPLOITBOT_CVE_EMBEDDER_PATH`, allowing deterministic
  QA without relying on local MLX embedding dependencies.
- `CVEService` records semantic search telemetry:
  `lastSemanticQuery`, `lastSemanticUsedEmbedding`, `lastSemanticFallback`,
  `lastSemanticResultCount`, vector dimensions, candidate count, and error text.
- `/state.cveSemantic` exposes that telemetry through the QA server.
- Added `seedSemanticProofFixture()` with two tiny stored vectors for a direct
  vector-ranking proof.
- Fixed CVE insert SQL by quoting the `"references"` column in both single and
  batch insert paths.
- Added `scripts/semantic-cve-proof.py`.

## Proof

- `python3 scripts/semantic-cve-proof.py`
- `swift build --package-path ExploitBot`
- `python3 scripts/context-catalog-proof.py`
- `python3 scripts/live-turn-harness.py`
- `python3 scripts/tool-catalog-proof.py`
- `cd ExploitBotEngine && PYTHONPATH=. uv run --extra dev pytest -q`
- `git diff --check`

The semantic proof launches the app with a fake embedder that writes a marker
file and returns `[1, 0, 0, 0]`, seeds one matching and one orthogonal CVE
embedding, requests a semantic context packet, and asserts:

- the fake embedder marker exists;
- `/state.cveSemantic.usedEmbedding=true`;
- `/state.cveSemantic.fallback=false`;
- `CVE-QA-SEMANTIC-HIT` appears in the context packet.

## Remaining

- Durable embeddings for non-CVE catalogue items are still a future lane:
  tools, techniques, findings, assets, commands, prior outputs, and stash items.
