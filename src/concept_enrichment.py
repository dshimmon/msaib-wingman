from concept_extractor import extract_concepts
from record_extractor import extract_records
from concept_registry import register_concepts


def enrich_concepts(knowledge_object):
    """
    Enrich a knowledge object with concepts and structured records.
    """

    concepts = extract_concepts(knowledge_object)
    knowledge_object["concepts"] = register_concepts(
        concepts,
        knowledge_object,
    )
    knowledge_object["records"] = extract_records(
        knowledge_object,
        knowledge_object["concepts"],
    )

    return knowledge_object