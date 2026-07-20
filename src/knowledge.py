import json
from pathlib import Path


def retrieve_evidence(topic):
    results = []
    normalized_topic = topic.lower()

    notes_folder = Path("data/notes")

    for note_file in notes_folder.glob("*.txt"):
        with open(note_file, "r") as file:
            notes = file.readlines()

        for line in notes:
            if normalized_topic in line.lower():
                results.append(
                    {
                        "domain": chunk["domain"],
                        "source": note_file.stem,
                        "location": None,
                        "text": line.strip(),
                        "id": None,
                        "section": None,
                        "concepts": [],
                        "records": [],
                    }
                )

    documents_folder = Path("data/documents")

    for json_file in documents_folder.rglob("*.json"):
        with open(json_file, "r") as file:
            chunks = json.load(file)

        for chunk in chunks:
            if normalized_topic in chunk["text"].lower():
                results.append(
                    {
                        "domain": note_file.stem,
                        "source": chunk["document"],
                        "location": chunk["location"],
                        "text": chunk["text"],
                        "id": chunk["id"],
                        "section": chunk["section"],
                        "concepts": chunk["concepts"],
                        "records": [],
                    }
                )

    return results