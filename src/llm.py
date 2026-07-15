import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def summarize_with_ai(topic, evidence):
    if not evidence:
        return (
            f"I couldn't find any notes related to '{topic}'. "
            "Try another topic or expand the knowledge base."
        )

    evidence_by_domain = {}

    for item in evidence:
        domain = item["domain"]
        evidence_by_domain.setdefault(domain, []).append(item["text"])

    domain_sections = []

    for domain, texts in evidence_by_domain.items():
        section = f"Course/Domain: {domain}\n" + "\n".join(texts)
        domain_sections.append(section)

    notes = "\n\n".join(domain_sections)

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