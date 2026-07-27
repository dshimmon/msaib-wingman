# Creates a structured evidence-gathering plan for study briefings.

import json
import re
from openai_client import client


MAX_BRIEFING_QUERIES = 5

BRIEFING_CATEGORIES = [
    "curriculum",
    "schedule",
    "dates",
    "preparation",
    "technology",
    "policies",
]

MODULE_REQUEST_PATTERN = re.compile(
    r"\b(?:(fall|spring|summer)\s+)?"
    r"(?:module|mod)\s+([ab])\b",
    re.IGNORECASE,
)

def create_module_briefing_plan(topic):
    """
    Create a consistent evidence plan for a module briefing.
    """
    match = MODULE_REQUEST_PATTERN.search(topic)

    if not match:
        return None

    season = match.group(1)
    module_letter = match.group(2).upper()

    if season:
        season = season.title()
        module_name = (
            f"{season} Module {module_letter}"
        )
    else:
        module_name = f"Module {module_letter}"

    if season:
        dates_question = (
            f"When does {module_name} begin, "
            f"and how is the {season.lower()} "
            "term structured?"
        )
    else:
        dates_question = (
            f"When does {module_name} begin, "
            "and how is its academic term structured?"
        )

    if season == "Fall":
        preparation_question = (
            "What summer work or preparation is "
            "recommended before the MSAIB fall term?"
        )
    elif season:
        preparation_question = (
            "What preparation is recommended before "
            f"the MSAIB {season.lower()} term?"
        )
    else:
        preparation_question = (
            "What preparation is recommended before "
            "beginning the MSAIB term?"
        )

    return {
        "briefing_title": (
            f"{module_name} Preparation Briefing"
        ),
        "retrieval_questions": [
            {
                "category": "curriculum",
                "question": (
                    f"Which courses are in {module_name} "
                    "for the full-time MSAIB program, "
                    "including course names and credit hours?"
                ),
            },
            {
                "category": "schedule",
                "question": (
                    "What are the documented class days "
                    f"and meeting times for {module_name} courses?"
                ),
            },
            {
                "category": "dates",
                "question": dates_question,
            },
            {
                "category": "preparation",
                "question": "Summer Work",
            },
            {
                "category": "technology",
                "question": (
                    "What are the MSAIB laptop "
                    "recommendations and computer requirements?"
                ),
            },
        ],
    }

def create_briefing_plan(topic):
    """
    Convert a briefing request into focused retrieval questions.
    """
    module_plan = create_module_briefing_plan(
        topic
    )

    if module_plan:
        return module_plan

    prompt = f"""
You are the study-briefing planner for Academic Wingman — Atlas.

Your only job is to decide which source evidence Atlas should
retrieve. Do not answer the user's request and do not create
recommendations yet.

Briefing topic:
{topic}

Available briefing categories:

curriculum
- Courses belonging to a term or module
- Course names and credit hours

schedule
- Known class days and meeting times

dates
- Known module start dates and documented term structure

preparation
- Documented preparation recommendations or prerequisite review

technology
- Documented laptop, software, or device requirements

policies
- Policies directly relevant to the requested topic

Rules:

- Produce no more than {MAX_BRIEFING_QUERIES} retrieval questions.
- Use only categories relevant to the briefing topic.
- Ask one focused factual question per retrieval.
- Every question must be understandable on its own.
- Keep every question scoped to the exact term, module, course,
  or topic named by the user.
- Curriculum, schedule, and dates may remain scoped to the
  requested term or module.
- Preparation and technology are usually program-wide.
  Do not repeat the module name in those questions unless
  the user explicitly asks for module-specific preparation
  or module-specific technology.
- For preparation evidence, prefer source-oriented wording
  such as:
  "What summer work or preparation is recommended before
  the MSAIB fall term?"
- For technology evidence, prefer source-oriented wording
  such as:
  "What are the MSAIB laptop recommendations and computer
  requirements?"
- Avoid adding broad contextual phrases such as "Fall 2026,"
  "Fall Module A," or "Mod A" when they are not necessary
  to retrieve the requested category.
- Prefer facts likely to appear in curriculum, onboarding,
  schedule, preparation, technology, or policy documents.
- Do not assume the user is enrolled in a particular section.
- Do not ask for instructors, rooms, modality, linked labs,
  tuition deadlines, immunizations, administrative holds,
  textbooks, syllabi, or course-site assignments unless the
  user explicitly asks about them.
- Do not ask for generic university information merely because
  it could theoretically be useful.
- Missing information will be reported later as an unknown.
- Avoid duplicate or overlapping questions.

For a request such as:
"Prepare me for Fall Module A."

A strong plan would ask focused questions such as:

- Which courses are in Fall Module A for the full-time MSAIB program?
- What are the known Fall Module A course days and times?
- When does Fall Module A begin and how is the term structured?
- What summer work or preparation is recommended before
  the MSAIB fall term?
- What are the MSAIB laptop recommendations and computer
  requirements?
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "briefing_plan",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "briefing_title": {
                            "type": "string",
                        },
                        "retrieval_questions": {
                            "type": "array",
                            "maxItems": MAX_BRIEFING_QUERIES,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "category": {
                                        "type": "string",
                                        "enum": BRIEFING_CATEGORIES,
                                    },
                                    "question": {
                                        "type": "string",
                                    },
                                },
                                "required": [
                                    "category",
                                    "question",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "briefing_title",
                        "retrieval_questions",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)