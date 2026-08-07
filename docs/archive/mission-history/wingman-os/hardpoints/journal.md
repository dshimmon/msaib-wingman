<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/wingman-os/hardpoints/mission.md",
  "archived_from": "docs/missions/wingman-os/hardpoints/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/wingman-os/hardpoints/mission.md`](../../../../missions/wingman-os/hardpoints/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 028 — Wingman Establishes the Hardpoints

**Call sign:** Hardpoints

**Product:** Wingman OS, with Atlas as the first implementing product

**Date:** August 6, 2026

**Correction date:** August 7, 2026

**Approval and commit date:** August 7, 2026

**Status:** Approved by Maverick, committed through the authorized bounded
Mission 028 closeout, and mission-complete; unpushed and unmerged

**Authorized baseline:**
`ea9f3e0baa1ad0eddba3cc8da358d7be4c76fd3c`

## Objective

Evolve the Airframe-era minimal product configuration into the smallest
explicit, typed, versioned Product Contract v1; route Atlas product decisions
through it; and prove the seam with a minimal test-only non-Atlas product
without adding product meaning or product-ID branches to Core.

## Verified starting state

- Repository root:
  `/Users/davidshimmon/Developer/Wingman/msaib-wingman`.
- Branch `main` at the exact authorized baseline, tracking `origin/main`, five
  commits ahead and zero behind according to cached Git metadata; no fetch was
  performed.
- Mission 027 implementation `e1570b0`, canonical reconciliation `7c3402c`,
  Vault reconciliation `4cabb43`, and baseline `ea9f3e0` are all ancestors of
  `HEAD`.
- The index and untracked inventory were empty. The only working-tree changes
  were the three disclosed `.DS_Store` files at repository root, `data/`, and
  `data/documents/`; they were preserved.
- Airframe's minimal contract existed at `src/product_contract.py` and was
  evolved in place.
- Ledger migration history was versions 1–3.
- The eligible offline baseline command was:

  `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest discover -s tests -p 'test_*.py'`

  Result: `Ran 201 tests in 2.215s` — `OK`.

The system `python3` and bundled workspace Python attempts were ineligible
because they lacked the repository version/dependencies. They failed before
the valid baseline and are recorded under limitations.

## Architecture decisions

1. `product_contract.py` remains the single Shared authority and now defines
   exact v1 validation, frozen declarations, capabilities, registry, and
   context. `ProductConfiguration` preserves its exact historical constructor
   as a deprecated input adapter that requires explicit completion into the
   authoritative `ProductContract`; it is not a competing contract type.
2. V1 compatibility is exact version 1. Unsupported, missing, boolean, or
   string versions fail before context construction.
3. `ProductRegistry` receives explicit definitions, sorts IDs
   deterministically, rejects duplicates/unknowns, becomes immutable after
   construction, and performs no discovery or imports.
4. `ProductContext` contains exactly one frozen contract. It is not a service
   locator. Shared requires it; Core never receives it.
5. `product_runtime.py` is the only new Shared runtime seam. It supplies
   product enrichment to Core, validates emitted records, applies declared
   metadata rules while preserving opaque metadata, and composes product
   interpretation with Core retrieval execution.
6. `product_config.py` is Atlas-owned after Hardpoints because it now supplies
   academic record shapes, metadata rules, retrieval policy, Briefing policy,
   UI terms, capabilities, and defaults. Its closed production registry
   contains Atlas only.
7. Terminal and Streamlit create explicit contexts. Atlas-owned facades retain
   fresh-context fallbacks only for supported callers that omit the new
   keyword.
8. The test product exists only in `tests/test_product_contract.py`, uses the
   ID `field-notes`, call sign `Beacon`, different UI/default/capabilities, one
   `field_note` record, and one `observation_kind` metadata rule. It is absent
   from production registration.
9. Ledger schema v3, source IDs, evidence, provenance, original paths and
   uploads, opaque metadata, and explicit-null precedence remain unchanged.
   Explicit-context intake applies only the selected product's declared rules,
   preserves undeclared values exactly, and injects no undeclared Atlas keys.

## Contract-demand map

| Element | Current demand |
|---|---|
| Version | Deterministic rejection before shared initialization. |
| Stable ID and display name | Durable internal identity and independently changeable UI text. |
| Capabilities | Current Chat, ingestion, retrieval, Briefing, and Library gating. |
| Record composition | Atlas curriculum/schedule extraction and the proof product's record. |
| Metadata declarations | Atlas upload/Library fields and the proof product's scoped normalizer. |
| Retrieval composition | Product interpretation before all current neutral Core retrieval modes. |
| Briefing composition | Current Atlas evidence planning and source-grounded generation. |
| Bounded UI vocabulary | Existing page, call sign, terminal, and workspace terms. |
| Default domain | Existing upload, CLI, and reprocessing fallback. |
| Registry and context | Explicit selection, early failures, immutability, and same-process isolation. |

No v1 field is reserved for future agents, tools, plugins, or a generic
extension bag.

## Implemented components

- Evolved `src/product_contract.py` and Atlas composition in
  `src/product_config.py`.
- Added neutral Shared composition in `src/product_runtime.py`.
- Propagated scoped context through terminal, Streamlit, Chat, retrieval,
  Briefing, ingestion, reprocessing, and removal paths while retaining
  compatibility call shapes.
- Corrected reprocessing to require both Library and ingestion before the
  first persistent index read, corrected explicit-context intake isolation,
  and restored the historical `ProductConfiguration` constructor through an
  explicit v1 conversion adapter.
- Extended architecture review for exact ownership, test-product vocabulary,
  and static product-ID behavior conditions.
- Added contract, registry, context, isolation, production-selection,
  metadata, record, real-seam, terminal, and Streamlit tests.
- Added the authoritative contract document, attachment guide, docs-only
  future attachment note, compatibility register, glossary updates, Airframe
  ownership updates, and README links.

## Verification

All successful verification after the dotenv issue used
`PYTHON_DOTENV_DISABLED=1` and the inert value
`OPENAI_API_KEY=mission-028-offline-placeholder`. No model call was made.

### Focused contract and architecture

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_product_contract tests.test_architecture_boundaries`

Result: `Ran 23 tests in 0.257s` — `OK`.

### Compatibility

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_airframe_composition tests.test_conversation_context tests.test_retrieval_pipeline`

Result: `Ran 29 tests in 0.010s` — `OK`.

### Atlas integration and parity

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_ingestion_integration tests.test_intake_service tests.test_library_management_service tests.test_library_service tests.test_source_registry tests.test_legacy_source_adapter tests.test_query_interpreter tests.test_retrieval_pipeline tests.test_briefing_planner tests.test_briefing_generator tests.test_briefing_service tests.test_briefing_persistence tests.test_conversation_context tests.test_airframe_composition`

Result: `Ran 121 tests in 0.361s` — `OK`. Logged diagnostic exceptions are
intentional negative-path assertions.

### Full suite

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest discover -s tests -p 'test_*.py'`

Result: `Ran 218 tests in 2.275s` — `OK`.

The final suite contains the 201-test starting baseline plus 15 Product
Contract tests and 2 additive architecture tests.

### Compilation and hygiene

`PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=/private/tmp/mission-028-pycache-20260806 .venv/flightline-py312/bin/python -m compileall -q src tests`

Result: exit 0, no output.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/flightline-py312/bin/python -c 'from ledger.migrations import MIGRATIONS; print([migration.version for migration in MIGRATIONS])'`

Result: `[1, 2, 3]`, exit 0.

`git diff --check`

Result: exit 0, no output. New untracked Mission 028 files were also scanned
directly for trailing whitespace; no matches were found.

## August 7 bounded read-only review corrections

Maverick authorized direct correction of exactly three findings from the first
read-only review:

1. Library reprocessing now requires both `SOURCE_LIBRARY` and
   `SOURCE_INGESTION` before loading the source registry, embedding index,
   concept registry, or knowledge file and before any reprocessing mutation.
   The contract does not impose a global Library-to-ingestion dependency;
   removal and other Library behavior still require only their actual
   capabilities.
2. Explicit-context upload intake now gives raw caller metadata to the selected
   product rules. Undeclared opaque values remain exact, Atlas metadata keys
   are added only when the selected contract declares them, and a non-null
   legacy Atlas argument for an undeclared field fails clearly. The no-context
   Atlas facade and explicit Atlas selection retain parity for Atlas's declared
   fields.
3. The exact Airframe-era `ProductConfiguration` constructor at the authorized
   HEAD is restored as a deprecated frozen input adapter. It is rejected by
   Product Context and Product Registry and supplies no v1 behavior or Atlas
   defaults. `to_product_contract()` requires all missing behavior and UI
   declarations and constructs the sole authoritative, normally validated
   `ProductContract`.

The four additive regressions are:

- `test_library_only_product_fails_before_reprocessing_state_access`;
- `test_explicit_non_atlas_intake_preserves_opaque_metadata`;
- `test_atlas_intake_legacy_and_explicit_context_match`; and
- `test_historical_product_configuration_converts_explicitly`.

### Focused rereview and Maverick disposition

The focused read-only reviewer inspected the three corrected implementations,
the four additive regressions, their adjacent behavior, and the related Mission
028 documentation. The reviewer found no remaining correction defect and
confirmed that all three original findings were fully corrected. The reviewer
also confirmed that the regressions exercise observable boundaries rather than
merely restating the implementation.

The rereview was marked `FAIL` solely because the reviewer opened the diff of
the excluded Flightline planning file
`docs/Wingman_Pre-Mission_028_Planning_Package.md` while classifying the
worktree. The file was not used in the technical judgment, no Flightline test
was run, and the repository remained unchanged. This was a review-boundary
breach, not a Mission 028 code or test defect.

Maverick explicitly overruled that procedural failure, accepted the focused
reviewer's technical evidence, waived another rereview, approved the Mission
028 code, and authorized mission closeout and the exact bounded commit. The
commit contains only the 23 Mission 028 proposal files. The seven rejected
Flightline correction files, failed-run evidence or retired envelopes, and the
three unrelated `.DS_Store` files remain excluded and uncommitted.

The focused correction and successful Atlas parity command was:

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_product_contract.ProductContractTests.test_library_only_product_fails_before_reprocessing_state_access tests.test_library_management_service.LibraryManagementServiceTests.test_successful_reprocessing tests.test_product_contract.ProductContractTests.test_explicit_non_atlas_intake_preserves_opaque_metadata tests.test_product_contract.ProductContractTests.test_atlas_intake_legacy_and_explicit_context_match tests.test_product_contract.ProductContractTests.test_historical_product_configuration_converts_explicitly -v`

Result: `Ran 5 tests in 0.006s` — `OK`.

Required module-level commands and results:

- `PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_product_contract`
  — `Ran 19 tests in 0.011s` — `OK`.
- `PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_architecture_boundaries`
  — `Ran 8 tests in 0.211s` — `OK`.
- `PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_intake_service tests.test_library_management_service`
  — `Ran 25 tests in 0.032s` — `OK`.

The same explicit non-Flightline repository module inventory that contained
184 tests before this correction was run without `tests.test_flightline`:

`PYTHON_DOTENV_DISABLED=1 OPENAI_API_KEY=mission-028-offline-placeholder PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 .venv/flightline-py312/bin/python -m unittest tests.test_airframe_composition tests.test_architecture_boundaries tests.test_briefing_generator tests.test_briefing_persistence tests.test_briefing_planner tests.test_briefing_service tests.test_conversation_context tests.test_excel_adapter tests.test_ingestion_integration tests.test_intake_service tests.test_ledger_core tests.test_legacy_source_adapter tests.test_library_management_service tests.test_library_service tests.test_pdf_adapter tests.test_product_contract tests.test_query_interpreter tests.test_retrieval_pipeline tests.test_source_registry tests.test_word_adapter`

Correction result: `Ran 188 tests in 0.824s` — `OK`. During the focused
rereview, the identical authorized non-Flightline inventory was run again:
`Ran 188 tests in 0.815s` — `OK`. The count is the authorized 184-test inventory
plus the four review regressions. Logged diagnostic exceptions are intentional
negative-path assertions.

`PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPYCACHEPREFIX=/private/tmp/mission-028-correction-compile-pycache-20260807 .venv/flightline-py312/bin/python -m compileall -q src`

Result: exit 0, no output.

`git diff --check`

Result: exit 0, no output.

## Compatibility

No supported facade was removed. The finite retained set, owners, reasons, and
removal conditions is in
`docs/architecture/Compatibility-Surfaces.md`. The old configuration class
name preserves its exact historical constructor through a deprecated input
adapter. The adapter cannot be registered or used as a Product Context; its
explicit completion method constructs the authoritative v1 type with normal
validation and no hidden product defaults. Existing module imports, CLI,
terminal, Streamlit, and monkeypatch surfaces continue to pass.

## Errors and limitations

- System Python 3.9 baseline attempt: 40 tests discovered, 16 import/runtime
  errors caused by the ineligible Python version and missing dependencies.
- Bundled workspace Python 3.12 attempt: 82 tests discovered, 15 import errors
  caused by missing repository dependencies.
- The first valid 201-test baseline did not disable the repository's import-time
  `load_dotenv()`. No model call or credential use occurred and this Engineer
  did not inspect `.env`, but an attempted credential-file read cannot be
  excluded. All remaining verification disabled dotenv and used an inert key.
- Three later safe-environment focused commands initially failed during import
  because an empty key is rejected by the OpenAI client constructor. Reruns
  with the inert placeholder passed.
- An initial Ledger-version inspection used the wrong import root and failed
  with `ModuleNotFoundError`; the corrected `PYTHONPATH=src` command returned
  `[1, 2, 3]`.
- That failed inspection created one ignored Python 3.12 cache file. It was
  moved intact to
  `/private/tmp/mission-028-generated-init-cpython-312.pyc`; pre-existing ignored
  caches were left untouched.
- The first 44-test correction-focused run had one test-only instrumentation
  error because a new mock handle was attached to the uploads `Path`. The
  capability failure itself occurred before state access. The mock wiring was
  corrected, and the identical command reran `Ran 44 tests in 0.042s` — `OK`;
  the final tree was then covered again by the 19-test contract and 25-test
  intake/Library commands above.
- The first independent read-only review returned three bounded findings. The
  focused reviewer confirmed all three direct corrections with no remaining
  technical finding. Its procedural `FAIL` resulted only from opening one
  excluded Flightline planning diff. Maverick explicitly overruled that
  procedural result, accepted the technical evidence, waived another rereview,
  and approved closeout. Crew Chief remains unimplemented and no Crew Chief
  audit is claimed.

## Safety and authority state

- No live Ledger write, migration, network model call, external service,
  real credential use, deployment, or live-data mutation was performed.
- Tests used temporary directories, temporary databases, patched storage
  paths, and mocked model behavior.
- Staging and commit were limited to the exact 23 authorized Mission 028 files.
  No fetch, push, merge, tag, release, deployment, or destructive Git action
  occurred.
- The three unrelated `.DS_Store` changes remain preserved and unstaged.
- Maverick approved Mission 028, authorized its exact bounded commit, and
  declared the mission closed. The resulting commit is unpushed and unmerged.
  No independent Crew Chief audit is claimed.

## Next gate

Maverick accepted the focused reviewer's technical confirmation, explicitly
overruled its Flightline-boundary procedural failure, waived another rereview,
and authorized this bounded Mission 028 commit. Mission 028 is approved,
committed, and closed. Any push, merge, deployment, or later contract change
requires a separate explicit authorization.
