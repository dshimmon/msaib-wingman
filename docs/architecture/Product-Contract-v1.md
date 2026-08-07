# Product Contract v1

**Mission:** 028 — Hardpoints

**Authority state:** Implemented and tested in the working tree; unapproved and
uncommitted

**Authoritative implementation:** `src/product_contract.py`

**Shared composition:** `src/product_runtime.py`

**First product definition:** `src/product_config.py`

## Purpose

Product Contract v1 is the one explicit attachment boundary between a product
and Wingman OS. A product owns meaning and policy. Shared composition validates
and applies that declaration. Core receives only neutral values, callbacks,
retrieval plans, declared record shapes, or opaque metadata.

Version compatibility is exact: this repository supports contract version `1`
only. Any other value fails while constructing the immutable definition, before
a Product Context or shared service can be initialized. This is version
validation, not a migration platform.

## Contract-demand map

| v1 element | Current demand | Atlas use |
|---|---|---|
| `contract_version` | Reject silent downgrade or coercion before composition. | Explicitly declares v1. |
| `product_key` / `product_id` | Ledger-facing and registry identity must remain stable and separate from display text. | `atlas`. |
| `product_name` / `display_name` | Page and application display text may change without changing internal identity. | `Academic Wingman`. |
| `capabilities` | Shared paths must fail before using behavior a product did not declare. | Chat, ingestion, retrieval, Briefing, and Library. |
| `records` | Current ingestion emits product-owned structured record types and needs a product-owned enricher. | Curriculum-course and course-schedule declarations plus academic enrichment. |
| `source_metadata_fields` | Upload and Library UI use declared fields and product rules while generic metadata remains opaque. | Program and academic-year fields with blank-text normalization and explicit-null preservation. |
| `retrieval` | Current queries require product interpretation before Core executes a neutral plan. | Academic query interpreter; all four retrieval modes still execute in Core. |
| `briefing` | Current Briefing requires product-owned evidence planning and source-grounded generation. | Atlas briefing planner and generator. |
| page, call-sign, terminal, and workspace terms | Current terminal and Streamlit roots display this bounded vocabulary. | Existing Atlas page, terminal, Chat, Briefing, and Library terms. |
| `default_domain` | Upload, CLI, and reprocessing need the current product default when no source domain is supplied. | `General`. |
| `ProductRegistry` | Selection must be explicit, deterministic, closed, and duplicate-safe. | Production registry contains Atlas only. |
| `ProductContext` | Shared work needs immutable per-composition scope without mutable global selection. | Fresh contexts are created by terminal, Streamlit, CLI, and compatibility boundaries. |

Every field above is exercised by Atlas or by the minimal test-only proof
product. V1 has no agent fields, tool fields, service locator, generic
extension bag, directory scan, import hook, or third-party loading mechanism.

## Typed structures and validation

- `ProductContract` is a frozen dataclass. Its nested record, retrieval,
  briefing, and metadata declarations are frozen; tuple and `frozenset`
  containers prevent post-registration mutation.
- `ProductConfiguration` is a deprecated Airframe-era input adapter with its
  exact historical constructor. It is not a contract and cannot be registered
  or placed in a Product Context. Its explicit `to_product_contract()` method
  requires the missing v1 behavior and UI declarations and returns a validated
  `ProductContract`; it supplies no product defaults.
- `ProductCapability` names only behavior currently used by Atlas.
- `RecordDeclaration` names one record type and its exact fields.
- `RecordComposition` binds those declarations to the product-owned enrichment
  callback.
- `SourceMetadataField` declares one metadata key, UI label, placeholder, and
  product-owned normalizer. Framework source fields are reserved and collisions
  fail immediately.
- `RetrievalComposition` supplies the interpreter that produces the four-field
  neutral retrieval plan.
- `BriefingComposition` supplies planning and generation callbacks only when
  the Briefing capability is declared.

Definitions fail early for unsupported versions, invalid IDs, empty required
UI/default values, invalid capabilities, missing record or retrieval
composition, Briefing capability/composition mismatches, duplicate record or
metadata declarations, invalid record shapes, and reserved metadata collisions.

## Registration and context

`ProductRegistry` receives an explicit iterable of already-imported
definitions. It creates a read-only, ID-sorted mapping, rejects duplicate IDs,
and rejects unknown selection with the registered IDs in the error. It never
scans directories or imports code.

`ProductContext` contains exactly one validated contract. It is immutable and
has no lookup methods for arbitrary services. A fresh context is passed from an
approved product-owned composition root. Shared code requires the context and
checks only neutral capabilities; Core never receives it.

The production registry in `product_config.py` contains only Atlas. The proof
product exists solely in `tests/test_product_contract.py`, uses a different ID,
display vocabulary, default, record declaration, metadata rule, and capability
set, and cannot be selected through the production registry.

## Shared execution seam

`product_runtime.py` provides four bounded operations:

1. Require an explicit, validated Product Context.
2. Create Core knowledge objects using the selected product's enricher, then
   validate emitted records against that product's declarations.
3. Apply normalizers only to declared source-metadata keys while preserving
   undeclared opaque values exactly.
4. Ask the product interpreter for a complete neutral retrieval plan and pass
   it with neutral retrieval callbacks to Core.

The same operations are exercised sequentially by Atlas and the test-only
product in one process. Their defaults, vocabulary, schemas, metadata rules,
and capabilities remain isolated.

Explicit-context upload intake passes caller values unchanged into this seam.
Only metadata fields declared by the selected product are normalized;
undeclared opaque values remain exact, and Atlas's `program` and
`academic_year` keys are not injected for a product that does not declare
them. A non-null Atlas legacy metadata argument is rejected when an explicitly
selected product does not declare that field rather than being ignored or
silently attached.

## Atlas composition

Atlas supplies all product-owned v1 decisions in `product_config.py`. Terminal
and Streamlit create explicit contexts. Atlas-owned compatibility facades pass
that context through Chat, ingestion, retrieval, Briefing, and Library
reprocessing/removal. Older supported callers that omit the new keyword receive
a fresh Atlas context inside an Atlas-owned facade; this compatibility behavior
does not place an Atlas default in Shared or Core. The no-context upload facade
retains its historical Atlas metadata merging and blank-text behavior; explicit
Atlas selection produces parity for the declared Atlas fields through the
Atlas contract normalizers.

## Source and Ledger invariants

Hardpoints does not change the Core knowledge-object shape, source IDs,
evidence items, provenance, uploaded originals, source URLs, original paths, or
source-enrichment flow. Undeclared nested metadata remains opaque. A present
metadata key remains authoritative even when its value is `null`.

Ledger migrations remain exactly versions 1–3. The private source-repository
adapter still mirrors the two historical physical columns and preserves its
existing missing-versus-explicit-null rules. No migration, Storage Port, live
write, or physical schema change is part of Product Contract v1.

## Supported v1 extension points

The complete extension surface is: identity/display fields, current capability
declarations, exact record declarations and enrichment, declared source
metadata rules, retrieval interpretation, optional Briefing composition,
bounded current UI terms, and the current default domain. Adding any other
contract field requires a later approved contract version or a separately
approved change justified by real product behavior.

Compatibility facades and their removal conditions are authoritative in
`docs/architecture/Compatibility-Surfaces.md`.
