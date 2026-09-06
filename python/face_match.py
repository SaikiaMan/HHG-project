import numpy as np


def cosine_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two face embeddings.

    Returns a value between -1 and 1.
    Higher values mean the embeddings are more similar.
    """

    embedding1 = np.array(embedding1)
    embedding2 = np.array(embedding2)

    similarity = np.dot(embedding1, embedding2) / (
        np.linalg.norm(embedding1) *
        np.linalg.norm(embedding2)
    )

    return float(similarity)


def is_match(embedding1, embedding2, threshold=0.5):
    """
    Determine whether two face embeddings are likely
    to belong to the same person.
    """

    similarity = cosine_similarity(
        embedding1,
        embedding2
    )

    return similarity >= threshold, similarity