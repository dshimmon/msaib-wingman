"""Authoritative machine-readable ownership for current Wingman packages."""


CORE = "wingman_core"
SHARED = "shared_product_framework"
ATLAS = "atlas"
RADAR = "radar"
COMPATIBILITY = "compatibility_facades"


MODULE_OWNERS = {
    "wingman": SHARED,
    "wingman.core": CORE,
    "wingman.shared": SHARED,
    "wingman.shared.compatibility": COMPATIBILITY,
    "products": SHARED,
    "products.atlas": ATLAS,
    "products.radar": RADAR,

    # Wingman OS Core
    "wingman.core.concept_registry": CORE,
    "wingman.core.concept_registry_storage": CORE,
    "wingman.core.concept_retrieval": CORE,
    "wingman.core.context_builder": CORE,
    "wingman.core.csv_adapter": CORE,
    "wingman.core.document_errors": CORE,
    "wingman.core.document_router": CORE,
    "wingman.core.embedding_indexer": CORE,
    "wingman.core.embedding_service": CORE,
    "wingman.core.embedding_storage": CORE,
    "wingman.core.evidence_ranker": CORE,
    "wingman.core.excel_adapter": CORE,
    "wingman.core.knowledge": CORE,
    "wingman.core.folder_intake": CORE,
    "wingman.core.knowledge_ingestion": CORE,
    "wingman.core.knowledge_loader": CORE,
    "wingman.core.ledger": CORE,
    "wingman.core.ledger.action_repository": CORE,
    "wingman.core.ledger.authorization": CORE,
    "wingman.core.ledger.backup": CORE,
    "wingman.core.ledger.briefing_repository": CORE,
    "wingman.core.ledger.database": CORE,
    "wingman.core.ledger.diagnostic_repository": CORE,
    "wingman.core.ledger.dry_run": CORE,
    "wingman.core.ledger.legacy_import_repository": CORE,
    "wingman.core.ledger.locking": CORE,
    "wingman.core.ledger.migrations": CORE,
    "wingman.core.ledger.models": CORE,
    "wingman.core.ledger.preservation": CORE,
    "wingman.core.ledger.readiness": CORE,
    "wingman.core.ledger.recovery": CORE,
    "wingman.core.ledger.source_repository": CORE,
    "wingman.core.ledger.transition": CORE,
    "wingman.core.ledger.transition_cli": CORE,
    "wingman.core.openai_client": CORE,
    "wingman.core.pdf_adapter": CORE,
    "wingman.core.powerpoint_adapter": CORE,
    "wingman.core.prompt_optimizer": CORE,
    "wingman.core.retrieval_engine": CORE,
    "wingman.core.section_resolver": CORE,
    "wingman.core.semantic_retriever": CORE,
    "wingman.core.semantic_similarity": CORE,
    "wingman.core.text_adapter": CORE,
    "wingman.core.word_adapter": CORE,

    # Shared Product Framework
    "wingman.shared.airframe_manifest": SHARED,
    "wingman.shared.briefing_persistence": SHARED,
    "wingman.shared.conversation_context": SHARED,
    "wingman.shared.diagnostic_service": SHARED,
    "wingman.shared.library_service": SHARED,
    "wingman.shared.product_contract": SHARED,
    "wingman.shared.product_runtime": SHARED,
    "wingman.shared.source_registry": SHARED,

    # Atlas product
    "products.atlas.batch_ingestion": ATLAS,
    "products.atlas.briefing_generator": ATLAS,
    "products.atlas.briefing_planner": ATLAS,
    "products.atlas.briefing_service": ATLAS,
    "products.atlas.bulk_ingestion": ATLAS,
    "products.atlas.canonicalizer": ATLAS,
    "products.atlas.concept_enrichment": ATLAS,
    "products.atlas.concept_extractor": ATLAS,
    "products.atlas.document_ingestion": ATLAS,
    "products.atlas.flight_cards_service": ATLAS,
    "products.atlas.intake_service": ATLAS,
    "products.atlas.interface": ATLAS,
    "products.atlas.library_management_service": ATLAS,
    "products.atlas.llm": ATLAS,
    "products.atlas.main": ATLAS,
    "products.atlas.product_config": ATLAS,
    "products.atlas.query_interpreter": ATLAS,
    "products.atlas.reasoning": ATLAS,
    "products.atlas.record_extractor": ATLAS,
    "products.atlas.retrieval_pipeline": ATLAS,
    "products.atlas.streamlit_app": ATLAS,
    "products.atlas.syllabus_intake": ATLAS,
    "products.atlas.ui": ATLAS,
    "products.atlas.ui.app": ATLAS,
    "products.atlas.ui.components": ATLAS,
    "products.atlas.ui.flight_cards": ATLAS,
    "products.atlas.ui.navigation": ATLAS,
    "products.atlas.ui.pages": ATLAS,
    "products.atlas.ui.pages.briefing": ATLAS,
    "products.atlas.ui.pages.chat": ATLAS,
    "products.atlas.ui.pages.cockpit": ATLAS,
    "products.atlas.ui.pages.course": ATLAS,
    "products.atlas.ui.pages.document": ATLAS,
    "products.atlas.ui.pages.library": ATLAS,
    "products.atlas.ui.pages.practice_test": ATLAS,
    "products.atlas.ui.pages.prompt_optimizer": ATLAS,
    "products.atlas.ui.pages.upload": ATLAS,
    "products.atlas.ui.shell": ATLAS,
    "products.atlas.ui.styles": ATLAS,
    "products.atlas.wingman_service": ATLAS,
}


ALLOWED_LAYER_DEPENDENCIES = {
    CORE: frozenset({CORE}),
    SHARED: frozenset({CORE, SHARED}),
    ATLAS: frozenset({CORE, SHARED, ATLAS}),
    RADAR: frozenset({CORE, SHARED, RADAR}),
    COMPATIBILITY: frozenset(
        {CORE, SHARED, ATLAS, RADAR, COMPATIBILITY}
    ),
}


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
    "streamlit": ATLAS,
}


TRANSITIONAL_EXCEPTIONS = {
    "flat_import_compatibility": {
        "modules": (
            "products.atlas.document_ingestion",
            "products.atlas.retrieval_pipeline",
            "products.atlas.wingman_service",
        ),
        "reason": (
            "Existing callers patch and import these public module names. "
            "They now compose lower-layer implementations without owning "
            "those mechanisms."
        ),
        "removal_stage": (
            "A future caller-migration mission, after supported imports and "
            "patch surfaces have documented replacements."
        ),
    },
    "historical_source_columns": {
        "modules": (
            "wingman.core.ledger.migrations",
            "wingman.core.ledger.source_repository",
        ),
        "reason": (
            "Applied migrations 1-3 are immutable history. Migration 4 "
            "removes the physical columns, while the version-3 rollback "
            "adapter remains supported for the governed rollback window."
        ),
        "removal_stage": (
            "After the separately approved rollback window closes."
        ),
    },
}
