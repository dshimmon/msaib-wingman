from canonicalizer import canonicalize_concept


def extract_concepts(knowledge_object):
    """
    Extract structured concepts from a knowledge object.
    """

    concepts = []

    heading = knowledge_object.get("heading")

    if heading:
        concepts.append(
            {
                "name": heading,
                "canonical": canonicalize_concept(heading),
            }
        )

    text = knowledge_object.get("text", "")

    for line in text.splitlines():
        columns = [column.strip() for column in line.split("|")]

        if len(columns) >= 3 and columns[1].isdigit():
            course_name = columns[2]

            concepts.append(
                {
                    "name": course_name,
                    "canonical": canonicalize_concept(course_name),
                }
            )

    return concepts