"""Build compact, source-grounded continuity for product conversations."""


MAX_CONVERSATION_TURNS = 3
MAX_EVIDENCE_ITEMS_PER_TURN = 5
MAX_TEXT_EXCERPT_CHARACTERS = 500


def compact_evidence_item(item):
    """
    Preserve useful source-grounded context without retaining prose.
    """
    concepts = []

    for concept in item.get("concepts", []):
        if isinstance(concept, dict):
            concept_name = (
                concept.get("canonical")
                or concept.get("name")
                or concept.get("id")
            )
        else:
            concept_name = str(concept)

        if concept_name:
            concepts.append(concept_name)

    text_excerpt = " ".join(
        (item.get("text") or "").split()
    )[:MAX_TEXT_EXCERPT_CHARACTERS]

    return {
        "source": item.get("source"),
        "location": item.get("location"),
        "heading": item.get("heading"),
        "section": item.get("section"),
        "concepts": concepts,
        "records": item.get("records", []),
        "text_excerpt": text_excerpt,
    }


def build_conversation_context(
    conversation_history,
    max_turns=MAX_CONVERSATION_TURNS,
):
    """
    Convert interface messages into recent source-grounded turns.
    """
    if not conversation_history:
        return []

    conversation_turns = []
    pending_question = None

    for message in conversation_history:
        role = message.get("role")

        if role == "user":
            pending_question = message.get(
                "content",
                "",
            ).strip()

        elif role == "assistant" and pending_question:
            evidence = [
                compact_evidence_item(item)
                for item in message.get(
                    "evidence",
                    [],
                )[:MAX_EVIDENCE_ITEMS_PER_TURN]
            ]

            conversation_turns.append(
                {
                    "user_question": pending_question,
                    "evidence": evidence,
                }
            )

            pending_question = None

    return conversation_turns[-max_turns:]
