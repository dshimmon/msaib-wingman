from concept_registry_storage import load_registry


def retrieve_concept_occurrences(search_terms):
    """
    Retrieve where matching concepts have appeared.
    """

    registry = load_registry()
    results = []
    seen_occurrences = set()

    normalized_terms = [
        term.lower().strip()
        for term in search_terms
        if term.strip()
    ]

    for registry_key, concept in registry.items():
        canonical = concept.get("canonical", "")

        searchable_concept = (
            f"{registry_key} {canonical}"
        ).lower()

        concept_matches = any(
            term in searchable_concept
            for term in normalized_terms
        )

        if not concept_matches:
            continue

        for occurrence in concept.get("occurrences", []):
            occurrence_key = (
                concept["id"],
                occurrence.get("document"),
                occurrence.get("location"),
            )

            if occurrence_key in seen_occurrences:
                continue

            seen_occurrences.add(occurrence_key)

            heading = occurrence.get("heading")
            canonical = concept["canonical"]

            results.append(
                {
                    "id": concept["id"],
                    "domain": "Concept Memory",
                    "source": occurrence.get("document"),
                    "heading": heading,
                    "section": None,
                    "concepts": [
                        {
                            "id": concept["id"],
                            "name": canonical,
                            "canonical": canonical,
                        }
                    ],
                    "records": [],
                    "location": occurrence.get("location"),
                    "text": (
                        f'{canonical} appeared under '
                        f'the heading "{heading}".'
                    ),
                }
            )

    return results