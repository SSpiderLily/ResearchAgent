from __future__ import annotations

import dashscope
from dashscope import TextEmbedding

from config import DASHSCOPE_API_KEY, EMBEDDING_MODEL

dashscope.api_key = DASHSCOPE_API_KEY

_BATCH_LIMIT = 10  # DashScope allows up to 10 texts per call


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using DashScope text-embedding API.

    Handles batching internally when the list exceeds the per-call limit.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_LIMIT):
        batch = texts[i : i + _BATCH_LIMIT]
        resp = TextEmbedding.call(model=EMBEDDING_MODEL, input=batch)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Embedding API error {resp.status_code}: {resp.message}"
            )

        batch_embeddings = [item["embedding"] for item in resp.output["embeddings"]]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
