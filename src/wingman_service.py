# Coordinates Wingman's complete question-answer process.

from reasoning import summarize_results
from retrieval_pipeline import retrieve_question_evidence


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

    return {
        "question": question,
        "query_plan": query_plan,
        "answer": answer,
        "evidence": evidence,
    }