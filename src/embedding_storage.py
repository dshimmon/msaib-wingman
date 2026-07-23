# Loads and saves embeddings for future semantic retrieval.

import json
from pathlib import Path


EMBEDDINGS_PATH = Path("data/embeddings/embeddings.json")


def load_embeddings():
    """
    Load stored embeddings.
    """

    if not EMBEDDINGS_PATH.exists():
        return {}

    with open(EMBEDDINGS_PATH, "r") as file:
        return json.load(file)


def save_embeddings(embeddings):
    """
    Save embeddings for future semantic retrieval.
    """

    EMBEDDINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(EMBEDDINGS_PATH, "w") as file:
        json.dump(
            embeddings,
            file,
            indent=4,
        )