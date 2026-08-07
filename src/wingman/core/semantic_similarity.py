# Measures semantic similarity between numerical embeddings.

import math


def calculate_similarity(first_embedding, second_embedding):
    """
    Compare two embeddings and return a similarity score.
    """

    if not first_embedding or not second_embedding:
        return 0.0

    if len(first_embedding) != len(second_embedding):
        raise ValueError(
            "Embeddings must contain the same number of values."
        )

    dot_product = sum(
        first_value * second_value
        for first_value, second_value in zip(
            first_embedding,
            second_embedding,
        )
    )

    first_length = math.sqrt(
        sum(value ** 2 for value in first_embedding)
    )

    second_length = math.sqrt(
        sum(value ** 2 for value in second_embedding)
    )

    if first_length == 0 or second_length == 0:
        return 0.0

    return dot_product / (
        first_length * second_length
    )