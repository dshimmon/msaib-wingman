# Compatibility Surface Register

**Status:** Mission 028 approved, committed, and closed; updated for the
unnumbered bulk-ingestion working mission.

Hardpoints removes no supported facade. The existing flat layout and patch
surfaces still have repository callers, so removing them would expand the
mission into an unrelated import migration. Each retained surface is finite and
forwards to the Product Contract or existing lower-layer owner.

| Retained surface | Owner | Reason retained | Objective removal condition |
|---|---|---|---|
| `ProductConfiguration` constructor | Shared Product Contract | Historical callers use the Airframe-era nine-field call shape. A deprecated frozen input adapter preserves that constructor and requires every missing v1 behavior declaration in `to_product_contract()` before it returns the sole authoritative `ProductContract`; the adapter itself is rejected by Product Context and Product Registry. | Supported callers construct `ProductContract` directly, adapter use is absent, and a compatibility-removal release is approved. |
| `product_config.ATLAS_PRODUCT` | Atlas | Existing tests and UI code read the immutable definition directly. | Supported callers use scoped contexts only and the constant has a documented replacement. |
| Optional `product_context` fallback in Atlas services | Atlas | Historical callers invoke Chat, ingestion, retrieval, Briefing, and Library functions without the new keyword. | Every supported caller passes context and parity tests prove fallback removal. |
| `document_ingestion` six-name export and CLI | Atlas | Existing imports, CLI behavior, and monkeypatch points depend on the flat facade. | A separately approved caller migration supplies stable replacement imports and CLI entrypoint. |
| `retrieval_pipeline.retrieve_question_evidence` and imported callback names | Atlas | Retrieval tests and callers patch the interpreter and Core callbacks at this module. | Callers migrate to an approved product-owned entrypoint with equivalent test seams. |
| `wingman_service` conversation-context re-exports | Atlas | Chat callers and tests import/patch the established names. | A caller inventory proves no supported imports remain. |
| `interface.show_header()` no-argument behavior | Atlas | Terminal callers rely on the existing Atlas header default. | Terminal composition always passes context and compatibility removal is separately approved. |
| `intake_service` `program` and `academic_year` keyword arguments | Atlas | Existing upload callers still use the pre-generic metadata arguments. | Callers use `product_metadata` exclusively and schema-v3 compatibility is independently resolved. |
| `intake_service.ingest_uploaded_document` single-file call | Atlas | Existing callers and tests ingest one named byte payload directly. Batch entry points call this same pipeline sequentially with atomic cleanup enabled; a one-file browser selection remains valid. | A separately approved caller migration provides an equivalent stable single-file API and proves all callers moved. |
| Version-3 source-column adapter | Core Ledger private adapter | Applied schema history and live compatibility require the physical columns while public metadata stays generic. | A separately authorized Ledger Transition after its assurance, backup, locking, dry-run, and rollback gates. |

## Removed surfaces

None. The Airframe-era `ProductConfiguration` constructor remains available as
a deprecated input adapter, not as a second contract model. It carries only its
historical values, supplies no Atlas or v1 behavior defaults, and cannot enter
Product Context or Product Registry. Migration is explicit: callers provide
the complete missing v1 declarations to `to_product_contract()` or construct
`ProductContract` directly; normal v1 validation remains authoritative.

The former claim that `product_config` was a neutral configuration owner was
superseded in architecture documentation because the module now composes
Atlas-owned academic policy. That is an ownership correction, not a runtime
facade removal.
