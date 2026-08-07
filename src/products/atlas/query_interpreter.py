# LLM interprets user query before asking Wingman
import json

from wingman.core.openai_client import client


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


def interpret_query(
    user_question,
    conversation_context=None,
):
    """
    Convert a natural-language question into
    structured retrieval instructions.
    """

    conversation_context = (
        conversation_context or []
    )

    if (
        is_bare_topic(user_question)
        and not conversation_context
    ):
        return {
            "memory_search_terms": [],
            "text_search_terms": [
                user_question.strip()
            ],
            "record_types": [],
            "record_filters": [],
        }
    conversation_context_text = json.dumps(
        conversation_context,
        indent=2,
    )
    prompt = f"""
You are the query interpreter for MSAIB Wingman.

Wingman is a deterministic knowledge operating system.
Your only job is to convert the user's question into
structured retrieval instructions.

Do not answer the question.

Recent source-grounded conversation context:
{conversation_context_text}

Conversation-context rules:

- Use recent context only to resolve pronouns, references,
  omitted subjects, and follow-up scope.
- Prior assistant wording is not provided and must not be
  treated as evidence.
- Prior evidence helps explain what the user means, but the
  retrieval plan must always retrieve fresh Wingman evidence.
- Prefer the most recent relevant conversation turn.
- Ignore conversation context when the current question is
  self-contained or clearly changes topics.
- Do not let earlier conversation override the current
  question.
- If prior evidence contains structured records, use their
  exact field values when resolving phrases such as:
  "those courses," "those classes," or "the second module."
- Multiple filters for the same field represent accepted
  alternatives.
- Different fields represent combined requirements.

Follow-up example:

Previous question:
"What classes will I take in the fall?"

Previous evidence:
curriculum_course records containing the Fall 2026 course
names.

Current question:
"Which of those meet on Tuesday?"

Interpretation:
- Request course_schedule records.
- Filter day = "Tuesday".
- Filter course_name using the relevant course names from
  the prior curriculum evidence.
- Retrieve fresh schedule evidence.

User question:
{user_question}

Available structured record types:

curriculum_course:
- program_format
- term
- module
- subject
- course_number
- course_name
- credit_hours
- is_alternative

course_schedule:
- module
- subject
- course_number
- course_name
- day
- start_time
- end_time

Use exact normalized record values when possible.

Normalized curriculum values:
- Full-time program becomes program_format = "Full-time"
- Part-time program becomes program_format = "Part-time"
- Fall for the current full-time cohort becomes term = "Fall 2026"
- Spring for the current full-time cohort becomes term = "Spring 2027"
- Fall Module A becomes module = "Mod A"
- Fall Module B becomes module = "Mod B"

Use curriculum_course records when the user asks:
- Which courses or classes are part of the curriculum
- What classes they will take
- Which courses belong to a term or module
- Course names or credit hours
- Fall or spring course listings

Examples:
- "What classes will I take in the fall?"
  uses curriculum_course with:
  program_format = "Full-time"
  term = "Fall 2026"

- "What classes are taken in the fall?"
  uses curriculum_course with:
  program_format = "Full-time"
  term = "Fall 2026"

- "Which courses are in Fall Module B?"
  uses curriculum_course with:
  program_format = "Full-time"
  term = "Fall 2026"
  module = "Mod B"

Use course_schedule records only when the user asks:
- When a class meets
- Which day a class meets
- Start or end times
- Meeting schedules
- Schedule options

Examples:
- "When is Decision Models?"
  uses course_schedule records.

- "What are the Fall Module A courses and times?"
  uses course_schedule with:
  module = "Mod A"

Do not use course_schedule merely because the user says
"class" or "course." A curriculum listing and a meeting
schedule are different kinds of knowledge.

Text search terms should be short phrases likely to appear
verbatim in source documents.

Record filters should represent exact field-value matches.

If structured records and record filters can fully answer
the user's question, return an empty text_search_terms list.

Only request document text when the question also requires
explanation, background, curriculum context, or other
information not contained in structured records.

Do not use structured records for a bare topic or for an
explanatory question such as "What is Decision Models?"

If the user provides only a short topic or noun phrase,
place that phrase in text_search_terms exactly as written.

Examples:
- "Orientation" becomes text_search_terms = ["Orientation"]
- "What is Orientation?" becomes text_search_terms = ["Orientation"]
- "What is Decision Models?" becomes text_search_terms = ["Decision Models"]

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