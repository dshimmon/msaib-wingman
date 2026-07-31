"""Authoritative machine-readable ownership for Mission 027 Airframe."""


CORE = "wingman_core"
SHARED = "shared_product_framework"
PRODUCT_SPECIFIC = "product_specific"
CONFIGURATION = "product_configuration"


MODULE_OWNERS = {
    # Wingman OS Core
    "concept_registry": CORE,
    "concept_registry_storage": CORE,
    "concept_retrieval": CORE,
    "context_builder": CORE,
    "document_router": CORE,
    "embedding_indexer": CORE,
    "embedding_service": CORE,
    "embedding_storage": CORE,
    "evidence_ranker": CORE,
    "excel_adapter": CORE,
    "knowledge": CORE,
    "knowledge_ingestion": CORE,
    "knowledge_loader": CORE,
    "ledger": CORE,
    "ledger.action_repository": CORE,
    "ledger.briefing_repository": CORE,
    "ledger.database": CORE,
    "ledger.diagnostic_repository": CORE,
    "ledger.legacy_import_repository": CORE,
    "ledger.migrations": CORE,
    "ledger.models": CORE,
    "ledger.source_repository": CORE,
    "openai_client": CORE,
    "pdf_adapter": CORE,
    "powerpoint_adapter": CORE,
    "retrieval_engine": CORE,
    "section_resolver": CORE,
    "semantic_retriever": CORE,
    "semantic_similarity": CORE,
    "word_adapter": CORE,

    # Shared Product Framework
    "airframe_manifest": SHARED,
    "briefing_persistence": SHARED,
    "conversation_context": SHARED,
    "diagnostic_service": SHARED,
    "library_service": SHARED,
    "product_contract": SHARED,
    "source_registry": SHARED,

    # Atlas-Specific
    "briefing_generator": PRODUCT_SPECIFIC,
    "briefing_planner": PRODUCT_SPECIFIC,
    "briefing_service": PRODUCT_SPECIFIC,
    "canonicalizer": PRODUCT_SPECIFIC,
    "concept_enrichment": PRODUCT_SPECIFIC,
    "concept_extractor": PRODUCT_SPECIFIC,
    "document_ingestion": PRODUCT_SPECIFIC,
    "intake_service": PRODUCT_SPECIFIC,
    "interface": PRODUCT_SPECIFIC,
    "library_management_service": PRODUCT_SPECIFIC,
    "llm": PRODUCT_SPECIFIC,
    "main": PRODUCT_SPECIFIC,
    "query_interpreter": PRODUCT_SPECIFIC,
    "reasoning": PRODUCT_SPECIFIC,
    "record_extractor": PRODUCT_SPECIFIC,
    "retrieval_pipeline": PRODUCT_SPECIFIC,
    "streamlit_app": PRODUCT_SPECIFIC,
    "wingman_service": PRODUCT_SPECIFIC,

    # Product Configuration
    "product_config": CONFIGURATION,
}


ALLOWED_LAYER_DEPENDENCIES = {
    CORE: frozenset({CORE}),
    SHARED: frozenset({CORE, SHARED}),
    PRODUCT_SPECIFIC: frozenset(
        {
            CORE,
            SHARED,
            PRODUCT_SPECIFIC,
            CONFIGURATION,
        }
    ),
    CONFIGURATION: frozenset(
        {SHARED, CONFIGURATION}
    ),
}


# A configuration import is an explicit composition-root decision. Adding
# another consumer requires an architecture review and manifest change.
DECLARED_CONFIGURATION_CONSUMERS = frozenset(
    {
        "main",
        "streamlit_app",
    }
)


# Core dependencies are intentionally closed. A new third-party dependency
# must be declared here and reviewed for product neutrality.
CORE_EXTERNAL_DEPENDENCIES = frozenset(
    {
        "docx",
        "dotenv",
        "openai",
        "openpyxl",
        "pptx",
        "pymupdf",
    }
)


PRODUCT_ONLY_EXTERNAL_DEPENDENCIES = {
    "streamlit": PRODUCT_SPECIFIC,
}


TRANSITIONAL_EXCEPTIONS = {
    "flat_import_compatibility": {
        "modules": (
            "document_ingestion",
            "retrieval_pipeline",
            "wingman_service",
        ),
        "reason": (
            "Existing callers patch and import these public module names. "
            "They now compose lower-layer implementations without owning "
            "those mechanisms."
        ),
        "removal_stage": (
            "Mission 028 Hardpoints, after stable product contracts expose "
            "replacement package entrypoints."
        ),
    },
    "historical_source_columns": {
        "modules": (
            "ledger.migrations",
            "ledger.source_repository",
        ),
        "reason": (
            "Applied migrations 1-3 are immutable history. Core exposes "
            "the two product-specific columns only through generic "
            "metadata while the physical version-3 schema remains in use."
        ),
        "removal_stage": (
            "Ledger Transition, after Assurance v1."
        ),
    },
}
