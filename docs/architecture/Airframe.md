# Airframe — Wingman Defines the Boundary

Mission 027, call sign **Airframe**

Mission 027 status: complete and committed in
`e1570b0c0d759933eaa0d2d0b48839051337d441` (`Establish product-neutral
Wingman Airframe`).

Mission 028 Hardpoints status: implemented and under review in the current
working tree; unapproved and uncommitted.

This document is the practical engineering guide for the current repository.
`src/airframe_manifest.py` is its machine-readable ownership inventory.
`tests/test_architecture_boundaries.py` performs bounded static review of the
real source tree.

## Governance scope

The Wingman Constitution is the ceremonial founder document; it is not yet
an automated compliance specification. Constitutional tests are a future,
CEO-approved capability under Wingman Assurance. Airframe does not claim
that static tests are a runtime security or authorization boundary.

Reserved powers include spending, changing or deleting shared truth, and
creating Git commits or merges. Mission 027 exercises none of them.

## Architecture

```text
Wingman OS Core <- Shared Product Framework <- Atlas
                          ^                    |
                          |                    |
                 Product Contract v1 <--------+
```

The repository keeps its flat public module names for compatibility:

- Core owns product-neutral Ledger, document, knowledge, retrieval,
  embedding, and evidence mechanisms.
- Shared owns reusable application services, Product Contract v1, scoped
  Product Context composition, source-registry behavior, conversation
  context, and ownership inventory.
- Atlas owns academic interpretation, enrichment, product-specific prompts,
  interfaces, source-management policy, contract composition, and production
  registration.

Core may import Core. Shared may import Core and Shared. Atlas may import Core,
Shared, and Atlas. Product selection is explicit at Atlas-owned composition
roots. The historical Product Configuration layer has no runtime module after
Hardpoints; `product_config` is Atlas-owned because it supplies Atlas policy.

Mission 027 does not add agents, plugins, Radar, authentication, cloud
storage, a new persistence engine, or Mission 028 packaging.

## Product-neutral seams

`knowledge_ingestion` creates, saves, and indexes generic knowledge objects.
It accepts enrichment as a callable. `document_ingestion` is the Atlas
compatibility facade and injects current concept/record enrichment.

The explicitly supported facade surface through Mission 028 is:

- `create_knowledge_objects`
- `extract_document_units`
- `index_knowledge_objects`
- `ingest_document`
- `resolve_section`
- `save_knowledge_objects`

`retrieval_engine` executes a supplied retrieval plan. Atlas interpretation
remains in `query_interpreter` and is composed by `retrieval_pipeline`.

`conversation_context` compacts prior source evidence. `wingman_service`
continues to re-export the established names while composing fresh retrieval
and Atlas reasoning.

`product_contract` is the single authoritative Product Contract v1. It
contains immutable typed definitions, exact-version validation, explicit
capabilities, record and metadata declarations, retrieval and briefing
composition, bounded UI terms, Product Registry, and Product Context.

`product_runtime` applies an explicit Product Context to the existing Core
ingestion and retrieval seams. It validates declared records and metadata
rules without interpreting product meaning. Core receives only callbacks,
plans, values, and opaque metadata.

`product_config` supplies Atlas's academic record declarations, metadata
normalizers, retrieval interpreter, briefing planner/generator, vocabulary,
defaults, and the closed production registry. The registry contains Atlas
only. It performs no scanning or dynamic loading.

`prompt_optimizer` is a product-neutral Core utility. It uses the existing
Core OpenAI client and receives only user-authored prompt text; it receives no
Product Context and contains no product vocabulary. The Atlas-owned Streamlit
composition root exposes it through an explicitly declared global shell
workspace, separate from the Chat, Briefing, and Library terms governed by
Product Contract v1.

## Version-3 Ledger compatibility

The physical Ledger schema remains exactly at migrations 1–3. Applied
migration history is immutable. The `sources.program` and
`sources.academic_year` columns are temporary legacy-storage exceptions;
they are not part of the public Core model or repository signature.

Private helpers in `ledger.source_repository` provide the only translation:

- Reads expose both values as ordinary generic metadata.
- A value already present in entity metadata wins over the legacy column.
- A missing metadata value falls back to the corresponding non-null column.
- Reads do not repair, reconcile, or otherwise mutate the database.
- Generic create and update operations mirror those two metadata keys into
  the version-3 columns until physical conversion occurs.

Mission 027 does not inspect or repair conflicts in live data. Physical
conversion and all related authorization, quiescence, backup, restoration,
and readiness work are deferred to **Ledger Transition after Assurance v1**.
There is no executable schema-transition procedure in this document.

## Runtime module inventory

The following inventory must exactly match `MODULE_OWNERS`.

### Wingman OS Core

- `concept_registry`
- `concept_registry_storage`
- `concept_retrieval`
- `context_builder`
- `document_router`
- `embedding_indexer`
- `embedding_service`
- `embedding_storage`
- `evidence_ranker`
- `excel_adapter`
- `knowledge`
- `knowledge_ingestion`
- `knowledge_loader`
- `ledger`
- `ledger.action_repository`
- `ledger.briefing_repository`
- `ledger.database`
- `ledger.diagnostic_repository`
- `ledger.legacy_import_repository`
- `ledger.migrations`
- `ledger.models`
- `ledger.source_repository`
- `openai_client`
- `pdf_adapter`
- `powerpoint_adapter`
- `prompt_optimizer`
- `retrieval_engine`
- `section_resolver`
- `semantic_retriever`
- `semantic_similarity`
- `word_adapter`

### Shared Product Framework

- `airframe_manifest`
- `briefing_persistence`
- `conversation_context`
- `diagnostic_service`
- `library_service`
- `product_contract`
- `product_runtime`
- `source_registry`

### Atlas-Specific

- `briefing_generator`
- `briefing_planner`
- `briefing_service`
- `canonicalizer`
- `concept_enrichment`
- `concept_extractor`
- `document_ingestion`
- `intake_service`
- `interface`
- `library_management_service`
- `llm`
- `main`
- `product_config`
- `query_interpreter`
- `reasoning`
- `record_extractor`
- `retrieval_pipeline`
- `streamlit_app`
- `wingman_service`

### Product Configuration

No runtime modules. The heading remains so the manifest/document parser and
historical ownership vocabulary stay explicit.

## Static review automation

The architecture test checks:

1. Every runtime Python module has exactly one manifest owner.
2. This inventory and the manifest contain the same modules and owners.
3. Local imports follow the declared dependency direction.
4. The historical configuration layer has no runtime consumers, and explicit
   product selection remains in Atlas-owned composition.
5. Core third-party dependencies remain in the reviewed allowlist.
6. Streamlit remains Atlas-owned.
7. High-signal product vocabulary is absent from executable Core and Shared
   string literals and identifiers except for exact version-3 storage
   locations. The historical SQL exception is bound to migration 1 and its
   statement identity; moving or duplicating it fails review.
8. Core and Shared contain no static behavior condition on a product ID.

These checks are useful review automation. They do not inspect runtime
values, authorize actions, sandbox code, or establish a security boundary.

## Transition register

- Flat compatibility modules remain after Hardpoints because supported callers
  still import and patch them. Their owners, reasons, and objective removal
  conditions are recorded in `Compatibility-Surfaces.md`.
- The historical `ProductConfiguration` constructor remains as a deprecated
  input adapter. It requires explicit completion into the authoritative
  `ProductContract` and is not accepted by Product Context or Product Registry.
- Atlas-owned facades may create a fresh Atlas context only when an older
  supported caller omits the new explicit context. Shared and Core never
  discover an Atlas default.
- The two physical source columns remain until Ledger Transition after
  Assurance v1.
- Ledger Transition must independently define authorization, quiescence,
  backup, restoration, readiness, conflict handling, and live-data runbooks.
- No transition code or live-data operation is authorized by Airframe.
