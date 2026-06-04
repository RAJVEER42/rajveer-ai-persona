"""Local embedding wrapper (bge-small via fastembed). Loaded once, reused.

Lives behind a tiny interface so the rest of the app never imports fastembed
directly — if we ever swap the model or move to a hosted embedder, only this
file changes.
"""
from __future__ import annotations
import numpy as np
from fastembed import TextEmbedding

from app import config

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(config.EMBED_MODEL)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized float32 vectors (cosine sim == inner product)."""
    import faiss
    vecs = np.array(list(_get_model().embed(texts)), dtype="float32")
    faiss.normalize_L2(vecs)
    return vecs


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]
