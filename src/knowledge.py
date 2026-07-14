import json
from pathlib import Path


def load_topics():
    with open("data/topics.json", "r") as file:
        return json.load(file)


def search_notes(topic):
    results = []
    notes_folder = Path("data/notes")

    for note_file in notes_folder.glob("*.txt"):
        with open(note_file, "r") as file:
            notes = file.readlines()

        for line in notes:
            if topic.lower() in line.lower():
                results.append((note_file.stem, line.strip()))

    return results