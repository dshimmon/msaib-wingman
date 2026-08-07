# Loads complete knowledge objects from stored document JSON files.

import json
from pathlib import Path


def load_knowledge_objects():
    """
    Load all stored knowledge objects.
    """

    knowledge_objects = []
    documents_folder = Path("data/documents")

    for json_file in documents_folder.rglob("*.json"):
        with open(json_file, "r") as file:
            document_objects = json.load(file)

        knowledge_objects.extend(document_objects)

    return knowledge_objects