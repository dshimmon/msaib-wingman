"""Product-neutral evidence retrieval from a supplied query plan."""

from wingman.core.concept_retrieval import retrieve_concept_occurrences
from wingman.core.evidence_ranker import rank_evidence
from wingman.core.knowledge import retrieve_evidence
from wingman.core.semantic_retriever import retrieve_semantic_evidence


MINIMUM_DETERMINISTIC_TEXT_SCORE = 3


def has_confident_deterministic_match(
    evidence,
    search_terms,
):
    """
    Determine whether deterministic evidence is sufficiently specific.
    """
    if not evidence:
        return False

    top_item = evidence[0]

    if (
        top_item.get("score", 0)
        < MINIMUM_DETERMINISTIC_TEXT_SCORE
    ):
        return False

    normalized_terms = [
        term.lower().strip()
        for term in search_terms
        if term.strip()
    ]

    if len(normalized_terms) <= 1:
        return True

    searchable_text = " ".join(
        [
            top_item.get("heading") or "",
            top_item.get("section") or "",
            top_item.get("text") or "",
        ]
    ).lower()

    matched_terms = {
        term
        for term in normalized_terms
        if term in searchable_text
    }

    return (
        any(
            len(term.split()) >= 2
            for term in matched_terms
        )
        or len(matched_terms) >= 2
    )


def retrieve_evidence_for_plan(
    question,
    query_plan,
    *,
    deterministic_retriever=retrieve_evidence,
    evidence_ranker=rank_evidence,
    semantic_retriever=retrieve_semantic_evidence,
    concept_retriever=retrieve_concept_occurrences,
):
    """
    Execute one product-supplied plan against Wingman evidence stores.
    """
    evidence = deterministic_retriever(query_plan)

    text_search_terms = query_plan.get(
        "text_search_terms",
        [],
    )

    records_requested = bool(
        query_plan.get("record_types")
        or query_plan.get("record_filters")
    )

    memory_requested = bool(
        query_plan.get("memory_search_terms")
    )

    text_only_request = bool(
        text_search_terms
        and not records_requested
        and not memory_requested
    )

    if text_only_request:
        evidence = evidence_ranker(
            evidence,
            text_search_terms,
        )

        if not has_confident_deterministic_match(
            evidence,
            text_search_terms,
        ):
            evidence = semantic_retriever(
                question,
                top_k=3,
            )

    memory_search_terms = query_plan.get(
        "memory_search_terms",
        [],
    )

    if memory_search_terms:
        evidence.extend(
            concept_retriever(memory_search_terms)
        )

    return evidence_ranker(
        evidence,
        text_search_terms,
    )
