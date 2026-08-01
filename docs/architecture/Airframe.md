# Airframe — Wingman Defines the Boundary

Mission 027, call sign **Airframe**

Status: complete and committed in
`e1570b0c0d759933eaa0d2d0b48839051337d441` (`Establish product-neutral
Wingman Airframe`).

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
                          ^
                          |
                Product Configuration
```

The repository keeps its flat public module names for compatibility:

- Core owns product-neutral Ledger, document, knowledge, retrieval,
  embedding, and evidence mechanisms.
- Shared owns reusable application services, the configuration contract,
  source-registry behavior, conversation context, and ownership inventory.
- Atlas owns academic interpretation, enrichment, prompts, recommendations,
  interfaces, source-management policy, and composition.
- Product Configuration supplies Atlas identity, visible labels, defaults,
  and its optional source-metadata fields.

Core may import Core. Shared may import Core and Shared. Atlas may import all
four layers. Configuration may import Shared and Configuration. Active
configuration is selected only by `main` and `streamlit_app`.

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

`ProductConfiguration` is intentionally small. It is not the Mission 028
plugin or extension contract.

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
- `query_interpreter`
- `reasoning`
- `record_extractor`
- `retrieval_pipeline`
- `streamlit_app`
- `wingman_service`

### Product Configuration

- `product_config`

## Static review automation

The architecture test checks:

1. Every runtime Python module has exactly one manifest owner.
2. This inventory and the manifest contain the same modules and owners.
3. Local imports follow the declared dependency direction.
4. Configuration has only the two declared composition-root consumers.
5. Core third-party dependencies remain in the reviewed allowlist.
6. Streamlit remains Atlas-owned.
7. High-signal product vocabulary is absent from executable Core and Shared
   string literals and identifiers except for exact version-3 storage
   locations. The historical SQL exception is bound to migration 1 and its
   statement identity; moving or duplicating it fails review.

These checks are useful review automation. They do not inspect runtime
values, authorize actions, sandbox code, or establish a security boundary.

## Transition register

- Flat compatibility modules remain until Mission 028 Hardpoints provides
  stable package entrypoints.
- The minimal configuration type remains intentionally incomplete until
  Mission 028.
- The two physical source columns remain until Ledger Transition after
  Assurance v1.
- Ledger Transition must independently define authorization, quiescence,
  backup, restoration, readiness, conflict handling, and live-data runbooks.
- No transition code or live-data operation is authorized by Airframe.
