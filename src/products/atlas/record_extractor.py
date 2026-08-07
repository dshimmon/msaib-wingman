# Extracts structured records from completed knowledge objects.

import re

from products.atlas.canonicalizer import canonicalize_concept


def normalize_module_header(line):
    """
    Convert curriculum and schedule module headings
    into one consistent value.
    """
    match = re.fullmatch(
        r"(?:fall|spring|summer)?\s*"
        r"(?:module|mod)\s+([ab])",
        line.strip(),
        re.IGNORECASE,
    )

    if not match:
        return None

    return f"Mod {match.group(1).upper()}"


def extract_term(line):
    """
    Extract an academic term from a line of text.
    """
    dated_term = re.search(
        r"\b(Fall|Spring|Summer)\s+\d{4}\b",
        line,
        re.IGNORECASE,
    )

    if dated_term:
        return dated_term.group(0).title()

    program_year_term = re.search(
        r"\bYear\s+(\d+)\s+"
        r"(Fall|Spring|Summer)\b",
        line,
        re.IGNORECASE,
    )

    if program_year_term:
        program_year = program_year_term.group(1)
        season = program_year_term.group(2).title()

        return f"Year {program_year} {season}"

    return None


def extract_records(knowledge_object, concepts):
    """
    Extract structured records from a knowledge object.
    """
    records = []
    text = knowledge_object.get("text", "")

    current_module = None
    current_term = None

    program_format = (
        "Part-time"
        if "part-time" in text.lower()
        else "Full-time"
    )

    concept_ids_by_canonical = {
        concept["canonical"]: concept["id"]
        for concept in concepts
    }

    for line in text.splitlines():
        stripped_line = line.strip()

        detected_term = extract_term(stripped_line)

        if detected_term:
            current_term = detected_term

        detected_module = normalize_module_header(
            stripped_line
        )

        if detected_module:
            current_module = detected_module
            continue

        columns = [
            column.strip()
            for column in stripped_line.split("|")
        ]

        if (
            len(columns) >= 6
            and columns[1].isdigit()
        ):
            records.append(
                {
                    "type": "course_schedule",
                    "module": current_module,
                    "subject": columns[0],
                    "course_number": columns[1],
                    "course_name": columns[2],
                    "concept_id": (
                        concept_ids_by_canonical.get(
                            canonicalize_concept(
                                columns[2]
                            )
                        )
                    ),
                    "day": columns[3].title(),
                    "start_time": columns[4],
                    "end_time": columns[5],
                }
            )

            continue

        if len(columns) < 3 or not current_module:
            continue

        course_code_match = re.fullmatch(
            r"(?:or\s+)?"
            r"([A-Za-z]{4})\s+"
            r"(\d{4})"
            r"(?:\*)?",
            columns[0],
            re.IGNORECASE,
        )

        if not course_code_match:
            continue

        subject = course_code_match.group(1).upper()
        course_number = course_code_match.group(2)
        course_name = columns[1]

        records.append(
            {
                "type": "curriculum_course",
                "program_format": program_format,
                "term": current_term,
                "module": current_module,
                "subject": subject,
                "course_number": course_number,
                "course_name": course_name,
                "concept_id": (
                    concept_ids_by_canonical.get(
                        canonicalize_concept(
                            course_name
                        )
                    )
                ),
                "credit_hours": columns[2],
                "is_alternative": (
                    stripped_line.lower().startswith(
                        "or "
                    )
                ),
            }
        )

    return records