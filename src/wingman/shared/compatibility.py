"""Registered aliases for supported historical module imports and scripts."""

from __future__ import annotations

import importlib
import runpy
import sys
from dataclasses import dataclass


CORE = "wingman-core"
SHARED = "shared-product-framework"
ATLAS = "atlas"


@dataclass(frozen=True)
class CompatibilityFacade:
    """One finite historical surface and its objective retirement gate."""

    historical: str
    canonical: str
    owner: str
    reason: str
    supported_callers: tuple[str, ...]
    removal_condition: str


def _facades(names, prefix, owner, reason, supported_callers):
    removal_condition = (
        "A separately approved caller-migration release proves every supported "
        "caller uses the canonical path and supplies equivalent entry-point "
        "and monkeypatch coverage."
    )
    return tuple(
        CompatibilityFacade(
            historical=name,
            canonical=f"{prefix}.{name}",
            owner=owner,
            reason=reason,
            supported_callers=supported_callers,
            removal_condition=removal_condition,
        )
        for name in names
    )


_CORE_MODULES = (
    "concept_registry",
    "concept_registry_storage",
    "concept_retrieval",
    "context_builder",
    "csv_adapter",
    "document_errors",
    "document_router",
    "embedding_indexer",
    "embedding_service",
    "embedding_storage",
    "evidence_ranker",
    "excel_adapter",
    "folder_intake",
    "knowledge",
    "knowledge_ingestion",
    "knowledge_loader",
    "openai_client",
    "pdf_adapter",
    "powerpoint_adapter",
    "prompt_optimizer",
    "retrieval_engine",
    "section_resolver",
    "semantic_retriever",
    "semantic_similarity",
    "text_adapter",
    "word_adapter",
)

_LEDGER_MODULES = (
    "ledger",
    "ledger.action_repository",
    "ledger.briefing_repository",
    "ledger.database",
    "ledger.diagnostic_repository",
    "ledger.legacy_import_repository",
    "ledger.migrations",
    "ledger.models",
    "ledger.source_repository",
)

_SHARED_MODULES = (
    "airframe_manifest",
    "briefing_persistence",
    "conversation_context",
    "diagnostic_service",
    "library_service",
    "product_contract",
    "product_runtime",
    "source_registry",
)

_ATLAS_MODULES = (
    "batch_ingestion",
    "briefing_generator",
    "briefing_planner",
    "briefing_service",
    "bulk_ingestion",
    "canonicalizer",
    "concept_enrichment",
    "concept_extractor",
    "document_ingestion",
    "intake_service",
    "interface",
    "library_management_service",
    "llm",
    "main",
    "product_config",
    "query_interpreter",
    "reasoning",
    "record_extractor",
    "retrieval_pipeline",
    "streamlit_app",
    "wingman_service",
)


COMPATIBILITY_FACADES = (
    *_facades(
        _CORE_MODULES,
        "wingman.core",
        CORE,
        "Historical callers import the former flat Core module path.",
        ("repository scripts", "external Python callers", "historical tests"),
    ),
    *_facades(
        _LEDGER_MODULES,
        "wingman.core",
        CORE,
        "Historical callers import the established ledger package path.",
        ("repository services", "external Python callers", "historical tests"),
    ),
    *_facades(
        _SHARED_MODULES,
        "wingman.shared",
        SHARED,
        "Historical callers import the former flat Shared module path.",
        ("repository services", "external Python callers", "historical tests"),
    ),
    *_facades(
        _ATLAS_MODULES,
        "products.atlas",
        ATLAS,
        "Atlas entry points, imports, and monkeypatch targets used the flat path.",
        (
            "terminal, Streamlit, and document/bulk CLIs",
            "external Python callers",
            "historical tests and monkeypatch targets",
        ),
    ),
)

FACADE_BY_HISTORICAL = {
    facade.historical: facade for facade in COMPATIBILITY_FACADES
}

if len(FACADE_BY_HISTORICAL) != len(COMPATIBILITY_FACADES):
    raise RuntimeError("Compatibility facade paths must be unique.")


def expose(module_name, historical):
    """Expose one canonical module through a registered historical name."""
    try:
        facade = FACADE_BY_HISTORICAL[historical]
    except KeyError as error:
        raise ImportError(
            f"Unregistered compatibility facade: {historical}"
        ) from error
    if module_name == "__main__":
        return runpy.run_module(facade.canonical, run_name="__main__")
    module = importlib.import_module(facade.canonical)
    sys.modules[module_name] = module
    if historical == "ledger":
        for child in COMPATIBILITY_FACADES:
            if not child.historical.startswith("ledger."):
                continue
            sys.modules[child.historical] = importlib.import_module(
                child.canonical
            )
    return module
