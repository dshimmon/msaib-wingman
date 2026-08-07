# Generates structured, source-grounded study briefings.

import json

from wingman.core.openai_client import client


def build_evidence_catalog(evidence):
    """
    Create labeled evidence entries that the briefing
    generator can reference safely.
    """
    evidence_reference_map = {}
    evidence_sections = []

    for evidence_number, item in enumerate(
        evidence,
        start=1,
    ):
        reference = f"E{evidence_number}"

        evidence_reference_map[reference] = {
            "source": item.get("source"),
            "location": item.get("location"),
            "heading": item.get("heading"),
        }

        evidence_section = [
            f"Evidence Reference: {reference}",
            f"Source: {item.get('source')}",
            f"Location: {item.get('location')}",
            f"Heading: {item.get('heading')}",
            f"Domain: {item.get('domain')}",
            "Text:",
            item.get("text", ""),
        ]

        records = item.get("records", [])

        if records:
            evidence_section.extend(
                [
                    "Structured Records:",
                    json.dumps(
                        records,
                        indent=2,
                    ),
                ]
            )

        evidence_sections.append(
            "\n".join(evidence_section)
        )

    return (
        evidence_reference_map,
        "\n\n".join(evidence_sections),
    )


def generate_study_briefing(
    topic,
    briefing_title,
    evidence,
):
    """
    Generate a structured briefing from supplied evidence.
    """
    if not evidence:
        return {
            "briefing": {
                "title": briefing_title,
                "overview": (
                    "Atlas does not currently have enough "
                    "source evidence to prepare this briefing."
                ),
                "verified_facts": [],
                "recommended_actions": [],
                "open_questions": [
                    {
                        "question": (
                            "Which additional sources should "
                            "be added to Atlas?"
                        ),
                        "why_it_matters": (
                            "The requested briefing could not "
                            "be grounded in existing knowledge."
                        ),
                    }
                ],
            },
            "evidence_reference_map": {},
        }

    (
        evidence_reference_map,
        evidence_catalog,
    ) = build_evidence_catalog(evidence)

    allowed_references = list(
        evidence_reference_map
    )

    prompt = f"""
You are Academic Wingman — Atlas.

Create a concise, practical, source-grounded study briefing.

Briefing request:
{topic}

Planned title:
{briefing_title}

Available evidence:
{evidence_catalog}

The output has three distinct responsibilities.

VERIFIED FACTS

- Include only facts directly supported by the evidence.
- Every verified fact must cite at least one evidence reference.
- Do not infer enrollment, instructors, classrooms, deadlines,
  assignments, or requirements that are not documented.
- Preserve important qualifications such as "subject to change."

RECOMMENDED ACTIONS

- Create useful actions based on the verified situation.
- Clearly treat these as Atlas recommendations, not source requirements.
- Every action must cite the evidence that motivated it.
- Do not invent mandatory obligations or deadlines.
- Prefer specific, realistic preparation actions.

OPEN QUESTIONS

- Identify meaningful information that the current evidence
  does not establish.
- Do not answer an open question by guessing.
- Do not create generic questions merely to fill the section.
- An empty list is acceptable when no important uncertainty remains.

GENERAL RULES

- Keep the briefing focused on the user's request.
- Separate facts from recommendations.
- Use only the supplied evidence references.
- Do not claim that a recommendation appeared in a source.
- Do not include a separate bibliography; Atlas will display
  the referenced evidence separately.
- Prioritize only the facts needed to prepare for the
  requested topic.

- Produce approximately 6–10 verified facts, 4–6
  recommended actions, and no more than 5 open questions.

- Do not include contacts, adjacent programs, unrelated
  semesters, or generic links unless directly necessary.

- Do not infer course-specific preparation topics merely
  from a course title.

- Do not assume the user can choose sections, is an
  international student, or has already been assigned
  particular classes or times.

- When several schedule options exist, identify the need
  to confirm the assigned section rather than recommending
  that the user choose one.

- Recommendations must be direct, practical consequences
  of the supplied evidence.

- Open questions should be important and actionable, not
  an exhaustive wishlist of information Atlas could obtain.
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "study_briefing",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                        },
                        "overview": {
                            "type": "string",
                        },
                        "verified_facts": {
                            "type": "array",
                            "maxItems": 10,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "category": {
                                        "type": "string",
                                    },
                                    "fact": {
                                        "type": "string",
                                    },
                                    "evidence_refs": {
                                        "type": "array",
                                        "minItems": 1,
                                        "items": {
                                            "type": "string",
                                            "enum": allowed_references,
                                        },
                                    },
                                },
                                "required": [
                                    "category",
                                    "fact",
                                    "evidence_refs",
                                ],
                                "additionalProperties": False,
                            },
                        },
                        "recommended_actions": {
                            "type": "array",
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "priority": {
                                        "type": "string",
                                        "enum": [
                                            "High",
                                            "Medium",
                                            "Low",
                                        ],
                                    },
                                    "action": {
                                        "type": "string",
                                    },
                                    "rationale": {
                                        "type": "string",
                                    },
                                    "evidence_refs": {
                                        "type": "array",
                                        "minItems": 1,
                                        "items": {
                                            "type": "string",
                                            "enum": allowed_references,
                                        },
                                    },
                                },
                                "required": [
                                    "priority",
                                    "action",
                                    "rationale",
                                    "evidence_refs",
                                ],
                                "additionalProperties": False,
                            },
                        },
                        "open_questions": {
                            "type": "array",
                            "maxItems": 5,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                    },
                                    "why_it_matters": {
                                        "type": "string",
                                    },
                                },
                                "required": [
                                    "question",
                                    "why_it_matters",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "title",
                        "overview",
                        "verified_facts",
                        "recommended_actions",
                        "open_questions",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return {
        "briefing": json.loads(
            response.output_text
        ),
        "evidence_reference_map": (
            evidence_reference_map
        ),
    }