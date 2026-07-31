# Coordinates Wingman's complete question-answer process.

from conversation_context import (
    MAX_CONVERSATION_TURNS,
    MAX_EVIDENCE_ITEMS_PER_TURN,
    MAX_TEXT_EXCERPT_CHARACTERS,
    build_conversation_context,
    compact_evidence_item,
)
from reasoning import summarize_results
from retrieval_pipeline import retrieve_question_evidence
from source_registry import enrich_evidence_sources


def ask_wingman(
    question,
    conversation_history=None,
):
    """
    Answer a question and return the complete result.
    """
    conversation_context = (
        build_conversation_context(
            conversation_history or []
        )
    )

    query_plan, evidence = retrieve_question_evidence(
        question,
        conversation_context=conversation_context,
    )

    answer = summarize_results(
        question,
        evidence,
    )

    display_evidence = enrich_evidence_sources(
        evidence
    )

    return {
        "question": question,
        "conversation_context": conversation_context,
        "query_plan": query_plan,
        "answer": answer,
        "evidence": display_evidence,
    }
