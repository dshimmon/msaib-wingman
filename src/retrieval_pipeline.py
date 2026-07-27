# Coordinates Wingman's complete evidence-retrieval process.

from concept_retrieval import retrieve_concept_occurrences
from evidence_ranker import rank_evidence
from knowledge import retrieve_evidence
from query_interpreter import interpret_query
from semantic_retriever import retrieve_semantic_evidence


MINIMUM_DETERMINISTIC_TEXT_SCORE = 3

def has_confident_deterministic_match(
    evidence,
    search_terms,
):
    """
    Determine whether the best deterministic result
    matches the user's intended topic strongly enough.
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

    has_specific_phrase = any(
        len(term.split()) >= 2
        for term in matched_terms
    )

    has_multiple_matches = (
        len(matched_terms) >= 2
    )

    return (
        has_specific_phrase
        or has_multiple_matches
    )


def retrieve_question_evidence(
    question,
    conversation_context=None,
):
    """
    Interpret a question and return its retrieval plan
    and ranked supporting evidence.
    """
    query_plan = interpret_query(
        question,
        conversation_context=conversation_context,
    )
    evidence = retrieve_evidence(query_plan)

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
        evidence = rank_evidence(
            evidence,
            text_search_terms,
        )

        if not has_confident_deterministic_match(
            evidence,
            text_search_terms,
        ):
            evidence = retrieve_semantic_evidence(
                question,
                top_k=3,
            )

    memory_search_terms = query_plan.get(
        "memory_search_terms",
        [],
    )

    if memory_search_terms:
        memory_evidence = retrieve_concept_occurrences(
            memory_search_terms
        )
        evidence.extend(memory_evidence)

    evidence = rank_evidence(
        evidence,
        text_search_terms,
    )

    return query_plan, evidence