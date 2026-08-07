# Coordinates evidence gathering and generation
# for Atlas study briefings.

import logging

from briefing_persistence import persist_generated_briefing
from briefing_generator import (
    generate_study_briefing,
)
from briefing_planner import (
    create_briefing_plan,
    create_module_briefing_plan,
)
from product_config import create_atlas_context
from product_contract import ProductCapability
from retrieval_pipeline import (
    retrieve_question_evidence,
)
from source_registry import enrich_evidence_sources
from diagnostic_service import new_trace_id, record_diagnostic


LOGGER = logging.getLogger(__name__)


EVIDENCE_LIMITS_BY_CATEGORY = {
    "curriculum": 1,
    "schedule": 1,
    "dates": 1,
    "preparation": 1,
    "technology": 1,
    "policies": 1,
}


def attempt_diagnostic(**arguments):
    """Keep a diagnostic failure from changing briefing behavior."""
    try:
        return record_diagnostic(**arguments)
    except Exception:
        LOGGER.exception(
            "Unexpected diagnostic failure "
            "(trace_id=%s, operation=%s)",
            arguments.get("trace_id"),
            arguments.get("operation"),
        )
        return None


def evidence_identity(item):
    """
    Create a stable identity for deduplicating evidence.
    """
    return (
        item.get("id"),
        item.get("source"),
        item.get("location"),
    )


def gather_briefing_evidence(
    topic,
    *,
    product_context=None,
):
    """
    Plan and execute the retrievals required for a briefing.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    context.require(ProductCapability.BRIEFING)
    briefing_plan = (
        context.product.briefing.plan_briefing(topic)
        if explicit_context
        else create_briefing_plan(topic)
    )
    planner_type = briefing_plan.get("planner_type")
    if planner_type is None:
        planner_type = (
            "deterministic_module"
            if create_module_briefing_plan(topic) is not None
            else "general_llm"
        )

    gathered_evidence = []
    retrieval_results = []
    seen_evidence = set()

    for planned_query in briefing_plan[
        "retrieval_questions"
    ]:
        category = planned_query["category"]
        question = planned_query["question"]

        if explicit_context:
            query_plan, evidence = retrieve_question_evidence(
                question,
                product_context=context,
            )
        else:
            query_plan, evidence = retrieve_question_evidence(
                question
            )

        retrieval_results.append(
            {
                "category": category,
                "question": question,
                "query_plan": query_plan,
                "evidence_count": len(evidence),
            }
        )

        evidence_limit = (
            EVIDENCE_LIMITS_BY_CATEGORY.get(
                category,
                1,
            )
        )

        for item in evidence[:evidence_limit]:
            identity = evidence_identity(item)

            if identity in seen_evidence:
                continue

            seen_evidence.add(identity)
            gathered_evidence.append(item)

    return {
        "topic": topic,
        "planner_type": planner_type,
        "briefing_title": briefing_plan[
            "briefing_title"
        ],
        "retrieval_results": retrieval_results,
        "evidence": gathered_evidence,
    }


def create_study_briefing(
    topic,
    *,
    briefing_id=None,
    persist=True,
    product_context=None,
):
    """
    Gather evidence and create one complete study briefing.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    context.require(ProductCapability.BRIEFING)
    trace_id = new_trace_id()
    try:
        if explicit_context:
            gathered_result = gather_briefing_evidence(
                topic,
                product_context=context,
            )
            briefing_generator = (
                context.product.briefing.generate_briefing
            )
        else:
            gathered_result = gather_briefing_evidence(topic)
            briefing_generator = generate_study_briefing
        generated_result = briefing_generator(
            topic=topic,
            briefing_title=gathered_result["briefing_title"],
            evidence=gathered_result["evidence"],
        )
        display_evidence = enrich_evidence_sources(
            gathered_result["evidence"]
        )
    except Exception as error:
        attempt_diagnostic(
            trace_id=trace_id,
            operation="briefing_generation",
            severity="error",
            recoverable=False,
            message="Briefing generation failed.",
            details={"error_type": type(error).__name__},
        )
        raise

    result = {
        "topic": topic,
        "retrieval_results": gathered_result["retrieval_results"],
        "briefing": generated_result["briefing"],
        "evidence_reference_map": generated_result[
            "evidence_reference_map"
        ],
        "evidence": display_evidence,
    }
    if not persist:
        result["persistence"] = {
            "status": "not_requested",
            "trace_id": trace_id,
        }
        return result

    try:
        persistence_payload = dict(result)
        persistence_payload["planner_type"] = gathered_result.get(
            "planner_type", "general_llm"
        )
        saved = persist_generated_briefing(
            persistence_payload,
            trace_id=trace_id,
            briefing_id=briefing_id,
        )
    except Exception as error:
        LOGGER.exception(
            "Briefing persistence failed (trace_id=%s)",
            trace_id,
        )
        attempt_diagnostic(
            trace_id=trace_id,
            operation="briefing_persistence",
            severity="error",
            recoverable=True,
            message="Generated briefing could not be saved.",
            details={"error_type": type(error).__name__},
            related_entity_id=briefing_id,
        )
        result["persistence"] = {
            "status": "failed",
            "trace_id": trace_id,
            "error": (
                str(error)
                if isinstance(error, KeyError)
                else "Briefing could not be saved."
            ),
        }
        return result

    for source_id in saved.unresolved_source_ids:
        attempt_diagnostic(
            trace_id=trace_id,
            operation="briefing_persistence",
            severity="warning",
            recoverable=True,
            message="Evidence source version could not be resolved.",
            related_entity_id=saved.briefing_version_id,
            details={"source_id": source_id},
        )
    attempt_diagnostic(
        trace_id=trace_id,
        operation="briefing_persistence",
        severity="info",
        recoverable=True,
        message="Briefing version persisted successfully.",
        related_entity_id=saved.briefing_version_id,
        details={
            "briefing_id": saved.briefing_id,
            "version_number": saved.version_number,
        },
    )
    result["persistence"] = {
        "status": "saved",
        "briefing_id": saved.briefing_id,
        "briefing_version_id": saved.briefing_version_id,
        "version_number": saved.version_number,
        "trace_id": saved.trace_id,
    }
    return result
