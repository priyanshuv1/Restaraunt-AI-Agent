from functools import lru_cache
import os

import numpy as np

MODEL_NAME = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIMENSIONS = 384


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the local embedding model once per process.

    The first load downloads model files if they are not cached yet. Subsequent
    calls reuse the same in-memory model.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return normalized 384-dimensional vectors for cosine search."""
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSIONS), dtype=np.float32)

    vectors = get_embedding_model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    if vectors.shape[1] != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS}-dimensional embeddings, "
            f"received {vectors.shape[1]}"
        )
    return vectors
