# Creates and stores embeddings for completed knowledge objects.

import hashlib

from embedding_service import create_embedding
from embedding_storage import load_embeddings, save_embeddings


def index_knowledge_objects(knowledge_objects):
    """
    Create embeddings for new or changed knowledge objects.
    """

    embeddings = load_embeddings()

    for knowledge_object in knowledge_objects:
        knowledge_id = knowledge_object["id"]
        knowledge_text = knowledge_object["text"]

        text_hash = hashlib.sha256(
            knowledge_text.encode("utf-8")
        ).hexdigest()

        existing_entry = embeddings.get(knowledge_id)

        if (
            isinstance(existing_entry, dict)
            and existing_entry.get("text_hash") == text_hash
        ):
            continue

        embeddings[knowledge_id] = {
            "text_hash": text_hash,
            "embedding": create_embedding(knowledge_text),
        }

    save_embeddings(embeddings)

    return embeddings