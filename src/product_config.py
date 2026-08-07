"""Atlas-owned Product Contract v1 composition and production registry."""

import re

from product_contract import (
    PRODUCT_CONTRACT_VERSION,
    BriefingComposition,
    ProductCapability,
    ProductContract,
    ProductRegistry,
    RecordComposition,
    RecordDeclaration,
    RetrievalComposition,
    SourceMetadataField,
)


def normalize_optional_text(value):
    """Atlas metadata rule preserving null and normalizing blank text."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def normalize_course_id(value):
    """Validate an explicitly assigned Atlas course identifier."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Course ID must be text.")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 120 or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:/ -]*",
        normalized,
    ):
        raise ValueError(
            "Course ID must start with a letter or number and use only "
            "letters, numbers, spaces, '.', '_', ':', '/', or '-'."
        )
    return normalized


def enrich_atlas_knowledge(knowledge_object):
    """Apply Atlas's existing academic enrichment callback."""
    from concept_enrichment import enrich_concepts

    return enrich_concepts(knowledge_object)


def interpret_atlas_query(
    question,
    conversation_context=None,
):
    """Apply Atlas's existing query interpretation policy."""
    from query_interpreter import interpret_query

    return interpret_query(
        question,
        conversation_context=conversation_context,
    )


def plan_atlas_briefing(topic):
    """Expose Atlas planning with its current persisted planner label."""
    from briefing_planner import (
        create_briefing_plan,
        create_module_briefing_plan,
    )

    plan = dict(create_briefing_plan(topic))
    if "planner_type" not in plan:
        plan["planner_type"] = (
            "deterministic_module"
            if create_module_briefing_plan(topic) is not None
            else "general_llm"
        )
    return plan


def generate_atlas_briefing(
    topic,
    briefing_title,
    evidence,
):
    """Apply Atlas's existing source-grounded briefing generator."""
    from briefing_generator import generate_study_briefing

    return generate_study_briefing(
        topic,
        briefing_title,
        evidence,
    )


ATLAS_PRODUCT = ProductContract(
    contract_version=PRODUCT_CONTRACT_VERSION,
    product_key="atlas",
    product_name="Academic Wingman",
    call_sign="Atlas",
    page_title="Atlas | Wingman",
    page_icon="🪿",
    default_domain="General",
    terminal_title="MSAIB WINGMAN",
    terminal_welcome="Welcome aboard, Maverick.",
    chat_label="Chat",
    library_label="Library",
    briefing_label="Briefing",
    capabilities=frozenset(
        {
            ProductCapability.SOURCE_GROUNDED_CHAT,
            ProductCapability.SOURCE_INGESTION,
            ProductCapability.EVIDENCE_RETRIEVAL,
            ProductCapability.BRIEFING,
            ProductCapability.SOURCE_LIBRARY,
        }
    ),
    records=RecordComposition(
        declarations=(
            RecordDeclaration(
                record_type="curriculum_course",
                fields=(
                    "program_format",
                    "term",
                    "module",
                    "subject",
                    "course_number",
                    "course_name",
                    "concept_id",
                    "credit_hours",
                    "is_alternative",
                ),
            ),
            RecordDeclaration(
                record_type="course_schedule",
                fields=(
                    "module",
                    "subject",
                    "course_number",
                    "course_name",
                    "concept_id",
                    "day",
                    "start_time",
                    "end_time",
                ),
            ),
        ),
        enrich_knowledge=enrich_atlas_knowledge,
    ),
    source_metadata_fields=(
        SourceMetadataField(
            key="course_id",
            label="Course ID",
            placeholder="Required for batch imports",
            normalizer=normalize_course_id,
        ),
        SourceMetadataField(
            key="program",
            label="Program",
            placeholder="Optional",
            normalizer=normalize_optional_text,
        ),
        SourceMetadataField(
            key="academic_year",
            label="Academic year",
            placeholder="Optional",
            normalizer=normalize_optional_text,
        ),
    ),
    retrieval=RetrievalComposition(
        interpret_query=interpret_atlas_query,
    ),
    briefing=BriefingComposition(
        plan_briefing=plan_atlas_briefing,
        generate_briefing=generate_atlas_briefing,
    ),
)


# Production selection is closed and explicit. Test definitions never enter it.
PRODUCTION_PRODUCT_REGISTRY = ProductRegistry(
    (ATLAS_PRODUCT,)
)


def create_product_context(product_id):
    """Select one explicitly registered production product."""
    return PRODUCTION_PRODUCT_REGISTRY.create_context(
        product_id
    )


def create_atlas_context():
    """Create a fresh immutable context for the Atlas composition root."""
    return create_product_context(
        ATLAS_PRODUCT.product_id
    )
