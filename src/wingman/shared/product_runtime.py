"""Shared composition that applies a Product Context to Core seams."""

from collections.abc import Mapping

from wingman.core.concept_retrieval import retrieve_concept_occurrences
from wingman.core.evidence_ranker import rank_evidence
from wingman.core.knowledge import retrieve_evidence
from wingman.core.knowledge_ingestion import (
    create_knowledge_objects as create_core_knowledge_objects,
)
from wingman.shared.product_contract import (
    ProductCapability,
    ProductContext,
    validate_product_metadata_key,
)
from wingman.core.retrieval_engine import retrieve_evidence_for_plan
from wingman.core.semantic_retriever import retrieve_semantic_evidence


RETRIEVAL_PLAN_FIELDS = frozenset(
    {
        "memory_search_terms",
        "record_filters",
        "record_types",
        "text_search_terms",
    }
)


def require_product_context(product_context):
    """Reject hidden or unvalidated product selection in shared code."""
    if not isinstance(product_context, ProductContext):
        raise TypeError(
            "Shared product composition requires an explicit "
            "Product Context."
        )
    return product_context


def validate_product_records(product_context, knowledge_objects):
    """Validate emitted product records against declared shapes."""
    context = require_product_context(product_context)
    declarations = {
        declaration.record_type: frozenset(declaration.fields)
        for declaration in context.product.records.declarations
    }
    for knowledge_object in knowledge_objects:
        for record in knowledge_object.get("records", []):
            if not isinstance(record, Mapping):
                raise ValueError(
                    "Product records must be mappings."
                )
            record_type = record.get("type")
            if record_type not in declarations:
                raise ValueError(
                    f"Undeclared product record type: {record_type!r}."
                )
            actual_fields = frozenset(record) - {"type"}
            declared_fields = declarations[record_type]
            if actual_fields != declared_fields:
                missing = sorted(
                    declared_fields - actual_fields
                )
                unexpected = sorted(
                    actual_fields - declared_fields
                )
                raise ValueError(
                    "Product record does not match its declaration; "
                    f"missing={missing}, unexpected={unexpected}."
                )
    return knowledge_objects


def create_product_knowledge_objects(
    product_context,
    file_path,
    domain,
    source_id=None,
    *,
    enricher=None,
    core_creator=create_core_knowledge_objects,
    unit_extractor=None,
    section_selector=None,
):
    """Create and validate source-backed objects through one shared seam."""
    context = require_product_context(product_context)
    context.require(ProductCapability.SOURCE_INGESTION)
    selected_enricher = (
        enricher
        if enricher is not None
        else context.product.records.enrich_knowledge
    )
    knowledge_objects = core_creator(
        file_path,
        domain,
        source_id=source_id,
        enricher=selected_enricher,
        unit_extractor=unit_extractor,
        section_selector=section_selector,
    )
    return validate_product_records(
        context,
        knowledge_objects,
    )


def normalize_source_metadata(product_context, metadata):
    """Apply declared rules while preserving undeclared opaque metadata."""
    context = require_product_context(product_context)
    context.require(ProductCapability.SOURCE_INGESTION)
    if not isinstance(metadata, Mapping):
        raise ValueError(
            "Product metadata must contain a mapping."
        )
    declarations = {
        field.key: field
        for field in context.product.source_metadata_fields
    }
    normalized = {}
    for key, value in metadata.items():
        validate_product_metadata_key(key)
        declaration = declarations.get(key)
        normalized[key] = (
            declaration.normalizer(value)
            if declaration is not None
            else value
        )
    return normalized


def retrieve_product_evidence(
    product_context,
    question,
    conversation_context=None,
    *,
    interpreter=None,
    deterministic_retriever=retrieve_evidence,
    evidence_ranker=rank_evidence,
    semantic_retriever=retrieve_semantic_evidence,
    concept_retriever=retrieve_concept_occurrences,
):
    """Interpret with product policy and execute through neutral Core."""
    context = require_product_context(product_context)
    context.require(ProductCapability.EVIDENCE_RETRIEVAL)
    selected_interpreter = (
        interpreter
        if interpreter is not None
        else context.product.retrieval.interpret_query
    )
    query_plan = selected_interpreter(
        question,
        conversation_context=conversation_context,
    )
    if not isinstance(query_plan, Mapping):
        raise ValueError(
            "Product retrieval interpretation must return a mapping."
        )
    missing_fields = RETRIEVAL_PLAN_FIELDS - set(query_plan)
    if missing_fields:
        raise ValueError(
            "Product retrieval plan is missing fields: "
            f"{sorted(missing_fields)}."
        )
    evidence = retrieve_evidence_for_plan(
        question,
        query_plan,
        deterministic_retriever=deterministic_retriever,
        evidence_ranker=evidence_ranker,
        semantic_retriever=semantic_retriever,
        concept_retriever=concept_retriever,
    )
    return query_plan, evidence
