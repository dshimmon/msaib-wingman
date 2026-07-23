# Retrieves knowledge objects by semantic similarity.

from embedding_service import create_embedding
from embedding_storage import load_embeddings
from knowledge_loader import load_knowledge_objects
from semantic_similarity import calculate_similarity


def retrieve_semantic_evidence(
    user_question,
    top_k=5,
    minimum_score=0.40,
):
    """
    Find the stored knowledge objects most similar
    in meaning to the user's question.
    """

    question_embedding = create_embedding(user_question)
    stored_embeddings = load_embeddings()
    knowledge_objects = load_knowledge_objects()

    knowledge_by_id = {
        knowledge_object["id"]: knowledge_object
        for knowledge_object in knowledge_objects
    }

    semantic_matches = []

    for knowledge_id, embedding_entry in stored_embeddings.items():
        if isinstance(embedding_entry, dict):
            knowledge_embedding = embedding_entry.get(
                "embedding",
                [],
            )
        else:
            knowledge_embedding = embedding_entry

        knowledge_object = knowledge_by_id.get(knowledge_id)

        if not knowledge_object:
            continue

        similarity_score = calculate_similarity(
            question_embedding,
            knowledge_embedding,
        )

        semantic_matches.append(
            {
                "id": knowledge_object["id"],
                "domain": knowledge_object["domain"],
                "source": knowledge_object["document"],
                "heading": knowledge_object.get("heading"),
                "section": knowledge_object.get("section"),
                "concepts": knowledge_object.get("concepts", []),
                "records": knowledge_object.get("records", []),
                "location": knowledge_object["location"],
                "text": knowledge_object["text"],
                "semantic_score": similarity_score,
            }
        )

    semantic_matches.sort(
        key=lambda match: match["semantic_score"],
        reverse=True,
    )

    strong_matches = [
        match
        for match in semantic_matches
        if match["semantic_score"] >= minimum_score
    ]

    return strong_matches[:top_k]