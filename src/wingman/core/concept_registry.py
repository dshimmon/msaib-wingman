# The single source of truth for every concept Wingman has learned.

import hashlib

from wingman.core.concept_registry_storage import (
    load_registry,
    save_registry,
)


def register_concepts(concepts, knowledge_object):
    """
    Assign stable IDs and register canonical concepts.
    """
    concept_registry = load_registry()
    registered_concepts = []
    registry_changed = False

    occurrence = {
        "document": knowledge_object["document"],
        "heading": knowledge_object["heading"],
        "location": knowledge_object["location"],
    }

    for concept in concepts:
        canonical = concept["canonical"]
        registry_key = canonical.lower()

        if registry_key not in concept_registry:
            concept_id = hashlib.sha256(
                registry_key.encode("utf-8")
            ).hexdigest()[:12]

            concept_registry[registry_key] = {
                "id": f"concept_{concept_id}",
                "canonical": canonical,
                "occurrences": [],
            }

            registry_changed = True

        concept_registry[registry_key].setdefault(
            "occurrences",
            [],
        )

        if (
            occurrence
            not in concept_registry[
                registry_key
            ]["occurrences"]
        ):
            concept_registry[
                registry_key
            ]["occurrences"].append(
                occurrence
            )

            registry_changed = True

        registered_concepts.append(
            {
                **concept,
                "id": concept_registry[
                    registry_key
                ]["id"],
            }
        )

    if registry_changed:
        save_registry(
            concept_registry
        )

    return registered_concepts