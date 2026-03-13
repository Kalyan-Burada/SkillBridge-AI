"""
embedding_module.py  —  SentenceTransformer wrapper for Career Copilot.

Loads the model once and caches it in memory.
All embeddings are L2-normalised so dot product == cosine similarity.
"""
from __future__ import annotations

from sentence_transformers import SentenceTransformer
import numpy as np

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embeddings(text_list: list) -> np.ndarray:
    """
    Encode a list of strings to L2-normalised 384-dim vectors.

    Args:
        text_list: list of strings to embed

    Returns:
        np.ndarray of shape (len(text_list), 384), L2-normalised
    """
    return _get_model().encode(
        text_list,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )