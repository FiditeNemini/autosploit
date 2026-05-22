# Checkpoint 126 - Settings category coverage proof

## Scope

- Prove Settings is organized as split pages/categories rather than one flat
  page.
- Make the Settings page structure inspectable through the QA state API.

## Changes

- Added `scripts/settings-category-coverage-proof.py`.
  - Seeds Settings visual state.
  - Verifies `/state.settingsCategoryCoverage.splitPages=true`.
  - Verifies all Settings categories are present in order:
    Engine, Model, Runtime, Context, Cache, Agents, CVE Database, Tools, Logs.
  - Verifies every category exposes title, subtitle, detail, icon, and expected
    page sections.
  - Switches each category through `POST /qa/settings-category` and verifies
    `/state.qaSettingsVisual.category` follows the selected page.
- Added `/state.settingsCategoryCoverage` with category metadata and page-section
  expectations.
- Updated the system review and flow inventory to list the Settings category
  coverage gate.

## Verification

- `python3 scripts/settings-category-coverage-proof.py`

## Notes

- This is a no-model Settings organization proof. Visual screenshots for
  selected model/engine/cache and status pages remain covered by the existing
  visual settings scripts.
