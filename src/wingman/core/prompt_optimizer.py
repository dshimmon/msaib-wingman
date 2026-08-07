"""Product-neutral AI prompt optimization."""

from wingman.core.openai_client import client


PROMPT_OPTIMIZER_MODEL = "gpt-5"

PROMPT_OPTIMIZER_INSTRUCTIONS = """
You are a prompt optimization assistant.

Rewrite the user's prompt so it is clear, specific, and effective while
preserving the user's original intent. Keep all supplied facts, constraints,
quoted text, and placeholders. Add useful structure, success criteria, and an
output format only when they improve the prompt. Do not answer the prompt. Do
not invent requirements or silently resolve ambiguity. Return only the
optimized prompt, with no preamble, explanation, or critique.
""".strip()


def optimize_prompt(prompt, *, response_client=client):
    """Return an AI-optimized prompt without changing its intent."""
    if not isinstance(prompt, str):
        raise TypeError("The prompt must be text.")

    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("Enter a prompt to optimize.")

    response = response_client.responses.create(
        model=PROMPT_OPTIMIZER_MODEL,
        instructions=PROMPT_OPTIMIZER_INSTRUCTIONS,
        input=normalized_prompt,
    )
    output_text = response.output_text
    if not isinstance(output_text, str) or not output_text.strip():
        raise RuntimeError(
            "The AI returned an empty optimized prompt. Please try again."
        )

    return output_text.strip()
