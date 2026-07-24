# Coordinates Wingman's complete evidence-retrieval process.

from concept_retrieval import retrieve_concept_occurrences
from evidence_ranker import rank_evidence
from knowledge import retrieve_evidence
from query_interpreter import interpret_query
from semantic_retriever import retrieve_semantic_evidence


def retrieve_question_evidence(question):
    """
    Interpret a question and return its retrieval plan
    and ranked supporting evidence.
    """
    query_plan = interpret_query(question)
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

    if (
        not evidence
        and text_search_terms
        and not records_requested
        and not memory_requested
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