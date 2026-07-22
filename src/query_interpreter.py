# LLM interprets user query before asking Wingman
import json

from openai_client import client


def is_bare_topic(user_question):
    """
    Determine whether the user entered a simple topic
    rather than a natural-language request.
    """

    cleaned_question = user_question.strip()

    if not cleaned_question:
        return False

    words = [
        word.strip(".,!?").lower()
        for word in cleaned_question.split()
    ]

    request_words = {
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "how",
        "list",
        "show",
        "find",
        "give",
        "course",
        "courses",
        "class",
        "classes",
        "schedule",
        "time",
        "times",
        "day",
        "days",
        "module",
    }

    return (
        not cleaned_question.endswith("?")
        and len(words) <= 6
        and not any(
            word in request_words
            for word in words
        )
    )


def interpret_query(user_question):
    """
    Convert a natural-language question into
    structured retrieval instructions.
    """

    if is_bare_topic(user_question):
        return {
            "memory_search_terms": [],
            "text_search_terms": [
                user_question.strip()
            ],
            "record_types": [],
            "record_filters": [],
        }

    prompt = f"""
You are the query interpreter for MSAIB Wingman.

Wingman is a deterministic knowledge operating system.
Your only job is to convert the user's question into
structured retrieval instructions.

Do not answer the question.

User question:
{user_question}

Available structured record type:

course_schedule:
- module
- subject
- course_number
- course_name
- day
- start_time
- end_time

Use exact normalized record values when possible.

Examples:
- "Fall Module A" becomes module = "Mod A"
- "Fall Module B" becomes module = "Mod B"
- "Tuesday classes" becomes day = "Tuesday"

Text search terms should be short phrases likely to appear
verbatim in source documents.

Record filters should represent exact field-value matches.

If structured records and record filters can fully answer
the user's question, return an empty text_search_terms list.

Only request document text when the question also requires
explanation, background, curriculum context, or other
information not contained in the structured records.

Use course_schedule records only when the user explicitly
asks for course listings, modules, class days, class times,
meeting times, or schedule details.

Do not use course_schedule records for a bare topic or for
an explanatory question such as "What is Decision Models?"

If the user provides only a short topic or noun phrase,
place that phrase in text_search_terms exactly as written.

Examples:
- "Orientation" becomes text_search_terms = ["Orientation"]
- "What is Orientation?" becomes text_search_terms = ["Orientation"]
- "What is Decision Models?" becomes text_search_terms = ["Decision Models"]
- "When is Decision Models?" uses course_schedule records

Use memory_search_terms when the user asks where,
when, or in which documents a concept has appeared.

Memory search terms should contain the concept itself,
not the full question.

Example:
"Where has MSAIB Curriculum appeared?"
becomes memory_search_terms = ["MSAIB Curriculum"].
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "retrieval_plan",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "memory_search_terms": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        "text_search_terms": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        "record_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        "record_filters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {
                                        "type": "string",
                                    },
                                    "value": {
                                        "type": "string",
                                    },
                                },
                                "required": [
                                    "field",
                                    "value",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "text_search_terms",
                        "record_types",
                        "record_filters",
                        "memory_search_terms",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)