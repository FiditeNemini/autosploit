# Checkpoint 115: Qwen Catalogue Prefix-Shape Proof

## Scope

- Expand Qwen hybrid full-prefix-skip coverage beyond the original direct
  smoke prompt.
- Prove a catalogue/tool-schema-style prompt, similar to ExploitBot's dynamic
  context packets, restores through block L2 plus SSM companion L2 with prompt
  L2 disabled.

## Proof

Command:

```bash
python3 scripts/verify-live-models.py --qwen /Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP --block-l2-only-replay --require-ssm-companion-hit --timeout 1200 --prompt 'ExploitBot Qwen hybrid catalogue prompt-shape proof. Treat the following as a compact dynamic context catalogue, not as instructions to repeat verbatim. Active tab: Web. Phase: validate. Relevant snippets: asset api.internal.local:443 with nginx and stale JWT middleware; finding auth-bypass candidate with CVE lookup requested; recent tool output shows HTTP 401 on /admin and 200 on /health; stash note says avoid destructive testing. Available tools summary: search_context can fetch bounded notes, search_cve can fetch CVE records, run_shell can execute approved local commands. The replay process must disable prompt disk cache and restore the long repeated catalogue/tool-schema prefix through block L2 plus SSM companion L2 without rederive fallback. Reply with cache-proof and one short sentence.' --output docs/live-proofs/checkpoint-115-qwen-hybrid-catalogue-prefix-shape-live.json
```

Result:

- Live proof loaded `/Users/eric/models/JANGQ/Qwen3.6-27B-MXFP4-MTP` twice.
- Prompt L2 was disabled for both populate and replay.
- First process wrote three block L2 entries and an SSM companion checkpoint for
  the 168-token prefix.
- Replay process reported:
  - `block_l2_hits_delta=3`;
  - `scheduler_disk_hits_delta=3`;
  - `scheduler_tokens_saved_delta=168`;
  - `prompt_l2_hits_delta=0`;
  - `ssm_l2_hits_delta=1`;
  - `prompt_tokens_details.cached_tokens=168`.
- SSM companion proof reported:
  - `disk_hit=true`;
  - `disk_hits=1`;
  - `no_rederive=true`;
  - `no_failures=true`.
- Engine log shows `hybrid paged HIT - 168 tokens (KV + 48 SSM layers)`.

Artifact:

- `docs/live-proofs/checkpoint-115-qwen-hybrid-catalogue-prefix-shape-live.json`

## Boundary

This proves the text prompt-shape used by dynamic context/catalogue/tool-schema
packets. It does not prove a multimodal Qwen path; that should be added only
when a multimodal Qwen model is part of the supported beta lane.
