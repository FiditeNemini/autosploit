# Deep Runtime/Tool-Flow Coverage

## Goal

Expose one app-backed beta gate for the runtime/tool-flow surfaces required for
usable beta hardening: tool flow, agent phases, bounded context, CVE taxonomy and
import, semantic CVE embeddings, supply-chain tools, stash retrieval, parser
coverage, streaming deltas, session workflows, and Qwen/MiniMax cache contracts.

## Changes

- Added `GET /qa/deep-runtime-flow-coverage`.
- Added `scripts/deep-runtime-flow-coverage-proof.py`.
- Extended `/qa/tool-flow-coverage` with explicit flow domains beyond the older
  tab-family list:
  - tool registry and execution
  - agent loop and live tool status
  - context retrieval and request audit
  - CVE taxonomy/import and semantic CVE embeddings
  - supply-chain tools
  - streaming responses and tool-call deltas
  - session workflows and parallel-agent settings
  - parser matrix
  - runtime cache and live cache artifacts
  - stash memory/retrieval
- Mirrored the deep gate through `/qa/coverage-index.groups.runtimeAndCache`.
- Mirrored the broader tool-flow domains through
  `/qa/coverage-index.groups.toolsAndParsers`.
- Updated the README beta status with the new deep-flow gate and the remaining
  live parallel-session/continuous-batching stress gap.

## Proof

Verified:

```bash
swift build --package-path ExploitBot -c debug
python3 scripts/deep-runtime-flow-coverage-proof.py
python3 scripts/tool-flow-coverage-proof.py
python3 scripts/coverage-index-proof.py
python3 scripts/app-qa-matrix-smoke-proof.py
python3 scripts/runtime-coverage-proof.py
python3 scripts/context-coverage-proof.py
python3 scripts/cve-taxonomy-coverage-proof.py
python3 scripts/supply-chain-cve-ui-proof.py
python3 scripts/session-coverage-proof.py
python3 scripts/session-workflow-matrix-proof.py
python3 scripts/chat-coverage-proof.py
python3 scripts/parser-tool-matrix-proof.py
python3 scripts/agent-loop-coverage-proof.py
python3 scripts/stash-coverage-proof.py
python3 scripts/semantic-cve-proof.py
python3 scripts/request-audit-proof.py
python3 scripts/proof-suite-inventory-proof.py
python3 scripts/proof-ledger-proof.py
python3 scripts/beta-readiness-coverage-proof.py
```

The first proof-suite inventory rerun timed out because the proof requested the
heavy `/qa/coverage-index` aggregate through an 8-second HTTP timeout. Measured
route time was about 6.4 seconds on this machine, so the harness timeout is now
20 seconds.

Proven by this checkpoint:

- Tool-schema cap for normal chat requests stays bounded at 12.
- Deployed agents can request the full registered tool schema set.
- Context injection remains capped at 4 snippets.
- CVE taxonomy includes local custom CVEs, supply-chain classes, and semantic
  embedding coverage.
- Stash retrieval remains part of bounded dynamic context instead of forcing all
  stash text into every prompt.
- Chat/agent routes expose streaming content, reasoning, usage, and tool-call
  delta handling.
- Runtime coverage still reports `prefix-cache-l2-turboquant`.
- Runtime coverage still reports prompt L2, block L2, paged KV, TurboQuant KV,
  SSM companion L2, and new-context cache-session preservation.
- Qwen hybrid SSM rederive live artifact is still present and OK.
- Qwen/MiniMax remain the only active beta supported families.

Still not proven:

- A realistic live parallel-session stress test with multiple concurrent agents
  and loaded model generation.
- Higher-cardinality continuous batching beyond the current two-request
  Qwen/MiniMax live proofs.
- Full manual native-app visual review across every tab/status/hover/detail
  state in the notarized release app.
