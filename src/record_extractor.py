from canonicalizer import canonicalize_concept

def extract_records(knowledge_object, concepts):
    """
    Extract structured records from a knowledge object.
    """

    records = []
    text = knowledge_object.get("text", "")
    current_module = None
    concept_ids_by_canonical = {
        concept["canonical"]: concept["id"]
        for concept in concepts
    }

    for line in text.splitlines():
        stripped_line = line.strip()

        if stripped_line.startswith("Mod "):
            current_module = stripped_line
            continue

        columns = [column.strip() for column in stripped_line.split("|")]

        if len(columns) >= 6 and columns[1].isdigit():
            records.append(
                {
                    "type": "course_schedule",
                    "module": current_module,
                    "subject": columns[0],
                    "course_number": columns[1],
                    "course_name": columns[2],
                    "concept_id": concept_ids_by_canonical.get(
                        canonicalize_concept(columns[2])
                    ),
                    "day": columns[3].title(),
                    "start_time": columns[4],
                    "end_time": columns[5],
                }
            )

    return records