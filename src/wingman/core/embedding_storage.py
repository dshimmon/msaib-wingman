# Loads and saves embeddings for future semantic retrieval.

import json
from pathlib import Path


EMBEDDINGS_PATH = Path(
    "data/embeddings/embeddings.json"
)


def load_embeddings():
    """
    Load stored embeddings.
    """
    if not EMBEDDINGS_PATH.exists():
        return {}

    with EMBEDDINGS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_embeddings(embeddings):
    """
    Save embeddings using an atomic replacement.
    """
    EMBEDDINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = Path(
        f"{EMBEDDINGS_PATH}.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            embeddings,
            file,
            indent=4,
        )

    temporary_path.replace(
        EMBEDDINGS_PATH
    )