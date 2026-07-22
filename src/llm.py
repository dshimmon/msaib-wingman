from context_builder import build_context
from openai_client import client


def summarize_with_ai(topic, evidence):
    if not evidence:
        return (
            f"I couldn't find any notes related to '{topic}'. "
            "Try another topic or expand the knowledge base."
        )

    notes = build_context(evidence)

    prompt = f"""
You are MSAIB Wingman.

Your job is to summarize study notes.

Topic:
{topic}

Notes:
{notes}

Write a concise study summary in 2–4 sentences.

Do not invent information.
Only summarize what is contained in the notes.
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )

    return response.output_text