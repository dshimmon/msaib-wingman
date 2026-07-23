#

from openai_client import client


def create_embedding(text):
    """
    Convert text into a numerical embedding.
    """

    if not text or not text.strip():
        return []

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    return response.data[0].embedding