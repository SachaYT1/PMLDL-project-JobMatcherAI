from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def get_encoder(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> SentenceTransformer:
    """Return a cached SentenceTransformer instance to avoid repeated downloads."""
    return SentenceTransformer(model_name)

