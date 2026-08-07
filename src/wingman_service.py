# Coordinates Wingman's complete question-answer process.

from conversation_context import (
    MAX_CONVERSATION_TURNS,
    MAX_EVIDENCE_ITEMS_PER_TURN,
    MAX_TEXT_EXCERPT_CHARACTERS,
    build_conversation_context,
    compact_evidence_item,
)
from product_config import create_atlas_context
from product_contract import ProductCapability
from reasoning import summarize_results
from retrieval_pipeline import retrieve_question_evidence
from source_registry import enrich_evidence_sources


def ask_wingman(
    question,
    conversation_history=None,
    *,
    product_context=None,
):
    """
    Answer a question and return the complete result.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    context.require(
        ProductCapability.SOURCE_GROUNDED_CHAT
    )
    conversation_context = (
        build_conversation_context(
            conversation_history or []
        )
    )

    retrieval_arguments = {
        "conversation_context": conversation_context,
    }
    if explicit_context:
        retrieval_arguments["product_context"] = context
    query_plan, evidence = retrieve_question_evidence(
        question,
        **retrieval_arguments,
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
