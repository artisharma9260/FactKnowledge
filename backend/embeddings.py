"""
Embeddings — generates and compares vector embeddings for facts.

Uses the Gemini text-embedding model. Cosine similarity is used for candidate
retrieval before the more expensive LLM comparison step.
"""

import logging
import math
import os
from typing import Any

import google.generativeai as genai

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
_SIMILARITY_THRESHOLD = float(os.getenv("EMBEDDING_SIMILARITY_THRESHOLD", "0.75"))


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #

async def embed_text(text: str) -> list[float]:
    """
    Return a unit-normalised embedding vector for `text`.
    Raises RuntimeError if the API key is not configured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model=_EMBEDDING_MODEL,
        content=text,
        task_type="SEMANTIC_SIMILARITY",
    )
    vector: list[float] = result["embedding"]
    return _normalise(vector)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity between two pre-normalised vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    # Clamp to [-1, 1] to guard against float precision edge cases
    return max(-1.0, min(1.0, dot))


def find_similar_facts(
    new_embedding: list[float],
    existing_facts: list[dict[str, Any]],
    threshold: float | None = None,
    top_k: int = 20,
) -> list[tuple[dict[str, Any], float]]:
    """
    Given a new fact's embedding and a list of existing fact dicts
    (each must have an 'embedding' key), return the top-k most similar
    existing facts above `threshold`, sorted descending by similarity.

    `existing_facts` dicts must contain at least: id, claim, embedding.
    """
    threshold = threshold if threshold is not None else _SIMILARITY_THRESHOLD
    scored: list[tuple[dict[str, Any], float]] = []

    for fact in existing_facts:
        emb = fact.get("embedding")
        if not emb or not isinstance(emb, list):
            continue
        try:
            score = cosine_similarity(new_embedding, emb)
        except ValueError:
            continue
        if score >= threshold:
            scored.append((fact, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# --------------------------------------------------------------------------- #
#  Internal
# --------------------------------------------------------------------------- #

def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]
