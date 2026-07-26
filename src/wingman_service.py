# Coordinates Wingman's complete question-answer process.

from reasoning import summarize_results
from retrieval_pipeline import retrieve_question_evidence
from source_registry import enrich_evidence_sources


def ask_wingman(question):
    """
    Answer a question and return the complete result.
    """
    query_plan, evidence = retrieve_question_evidence(
        question
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
        "query_plan": query_plan,
        "answer": answer,
        "evidence": display_evidence,
    }