import os

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def generate_embedding(text: str) -> list[float]:
    embedding = get_embedding_model().encode(text)
    return embedding.tolist()
