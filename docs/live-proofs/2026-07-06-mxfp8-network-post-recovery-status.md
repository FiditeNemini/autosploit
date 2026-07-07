# 2026-07-06 MXFP8 Network/Post Recovery Status

Status: PASS for the 27B MXFP8 natural network/post app-backed proof.

## Live proof

- Artifact: `docs/live-proofs/2026-07-06-real-qwen-natural-network-credential-post-27b-mxfp8.json`
- mtime: `2026-07-06 23:05:35 PDT`
- Model: `/Users/eric/models/dealign.ai/Qwen3.6-27B-MXFP8-CRACK-MTP`
- Result: `ok=true`, `overall=PASS`
- Tool sequence: `nmap -> httpx -> hydra -> netexec -> run_shell -> linpeas`
- Raw tools: `nmap`, `httpx`, `hydra`, `netexec`, `run_shell`, `linpeas`

## PASS rows inspected

- `modelSelectedNetworkToolSequence=PASS`
- `realQwenDroveNaturalNetworkCredentialPost=PASS`
- `naturalNetworkToolCoverage=PASS`
- `credentialProof=PASS`
- `networkHostEvidence=PASS`
- `postCheckProof=PASS`
- `reportGeneratedFromEvidence=PASS`
- `turboQuantKV=PASS`
- `prefixCache=PASS`
- `pagedCache=PASS`
- `blockDiskCache=PASS`
- `hybridAsyncSSMReDerive=PASS`
- `nativeD3MTPForMTPModel=PASS`

## Root causes fixed before PASS

1. The natural network/post prompt only listed `hydra` as a relevant schema. MXFP8 could drift toward shell/curl language for the seeded login check. The prompt now explicitly says: `Use hydra for seeded demo/demo credential validation; do not use run_shell for the credential check.`
2. The app's explicit-deny guard treated that credential-only `run_shell` restriction as a global shell ban and blocked the allowed `/post-check` command. `ChatService.autopilotToolPolicy` now allows the narrow contextual case only when the prompt also explicitly allows `run_shell` for `/post-check`, the command contains `/post-check`, and the command target is local.

## Boundary

The PASS includes app-bounded recovery: `requestContext.streamWarnings` contains `autoLinpeasAfterPostCheckMarkerFallback`. This proves the app can safely complete the requested linpeas step after confirmed post-check evidence, but it is not a claim that MXFP8 independently emitted every final tool call without recovery.

This proof covers 27B MXFP8 for the network credential/post fixture. It does not cover 35B MXFP8, visible Computer Use UI interaction, or all non-network scenario classes.

## Verification

- `PYTHONPATH=ExploitBotEngine ExploitBotEngine/.venv/bin/python -m pytest -q ExploitBotEngine/testsuite` -> `461 passed, 3 warnings`
- `swift build --package-path ExploitBot -c debug` -> build complete
- `git diff --check` -> clean
