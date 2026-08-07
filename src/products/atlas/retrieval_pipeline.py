# Atlas composition for product policy and Core evidence retrieval.

from wingman.core.concept_retrieval import retrieve_concept_occurrences
from wingman.core.evidence_ranker import rank_evidence
from wingman.core.knowledge import retrieve_evidence
from products.atlas.product_config import create_atlas_context
from wingman.shared.product_runtime import retrieve_product_evidence
from products.atlas.query_interpreter import interpret_query
from wingman.core.retrieval_engine import (
    MINIMUM_DETERMINISTIC_TEXT_SCORE,
    has_confident_deterministic_match,
    retrieve_evidence_for_plan,
)
from wingman.core.semantic_retriever import retrieve_semantic_evidence


def retrieve_question_evidence(
    question,
    conversation_context=None,
    *,
    product_context=None,
):
    """
    Interpret a question and return its retrieval plan
    and ranked supporting evidence.
    """
    explicit_context = product_context is not None
    context = (
        product_context
        if explicit_context
        else create_atlas_context()
    )
    return retrieve_product_evidence(
        context,
        question,
        conversation_context=conversation_context,
        interpreter=(
            None
            if explicit_context
            else interpret_query
        ),
        deterministic_retriever=retrieve_evidence,
        evidence_ranker=rank_evidence,
        semantic_retriever=retrieve_semantic_evidence,
        concept_retriever=retrieve_concept_occurrences,
    )
