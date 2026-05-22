# Checkpoint 119: Parsed Result Context Retrieval Proof

## Scope

- Prove parsed tool results do not stop at tab state.
- Ensure representative parsed outputs can be retrieved through the bounded
  dynamic context catalogue used by chat and `search_context`.
- Add post-exploitation attribution rows to the catalogue so parsed host/user
  facts are not lost once raw output falls out of the recent-output window.

## Changes

- Added `scripts/result-context-catalog-proof.py`.
- Added `post.attribution` context catalogue items from
  `ResultsStore.postAttributions`.
- Updated the system review and flow inventory so result-to-context routing is
  a repeatable proof gate.

## Proof

Command:

```bash
python3 scripts/result-context-catalog-proof.py
```

Result:

- The proof first failed because parsed `linpeas` attribution rows were not
  indexed by the context catalogue.
- After adding `post.attribution` items, the proof passed and verified:
  - parsed `linpeas` host/user attribution is retrieved as
    `[post.attribution]`;
  - parsed hashcat credential findings are retrieved by targeted credential
    query;
  - parsed nmap port assets are retrieved by targeted service query;
  - parsed nuclei CVE findings are retrieved by targeted CVE query;
  - non-CVE embedding sources include `asset.port`, `finding`, and
    `post.attribution`.

## Boundary

This proves the parsed-result-to-context lane for representative current output
shapes. It does not claim every possible external tool output variant is
semantically normalized; parser-specific expansion remains an ongoing proof
surface.
