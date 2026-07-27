# Coordinates evidence gathering and generation
# for Atlas study briefings.

from briefing_generator import (
    generate_study_briefing,
)
from briefing_planner import create_briefing_plan
from retrieval_pipeline import (
    retrieve_question_evidence,
)
from source_registry import enrich_evidence_sources


EVIDENCE_LIMITS_BY_CATEGORY = {
    "curriculum": 1,
    "schedule": 1,
    "dates": 1,
    "preparation": 1,
    "technology": 1,
    "policies": 1,
}


def evidence_identity(item):
    """
    Create a stable identity for deduplicating evidence.
    """
    return (
        item.get("id"),
        item.get("source"),
        item.get("location"),
    )


def gather_briefing_evidence(topic):
    """
    Plan and execute the retrievals required for a briefing.
    """
    briefing_plan = create_briefing_plan(topic)

    gathered_evidence = []
    retrieval_results = []
    seen_evidence = set()

    for planned_query in briefing_plan[
        "retrieval_questions"
    ]:
        category = planned_query["category"]
        question = planned_query["question"]

        query_plan, evidence = (
            retrieve_question_evidence(
                question
            )
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
        "briefing_title": briefing_plan[
            "briefing_title"
        ],
        "retrieval_results": retrieval_results,
        "evidence": gathered_evidence,
    }


def create_study_briefing(topic):
    """
    Gather evidence and create one complete study briefing.
    """
    gathered_result = gather_briefing_evidence(
        topic
    )

    generated_result = generate_study_briefing(
        topic=topic,
        briefing_title=gathered_result[
            "briefing_title"
        ],
        evidence=gathered_result["evidence"],
    )

    display_evidence = enrich_evidence_sources(
        gathered_result["evidence"]
    )

    return {
        "topic": topic,
        "retrieval_results": gathered_result[
            "retrieval_results"
        ],
        "briefing": generated_result[
            "briefing"
        ],
        "evidence_reference_map": (
            generated_result[
                "evidence_reference_map"
            ]
        ),
        "evidence": display_evidence,
    }