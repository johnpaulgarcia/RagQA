from __future__ import annotations

import httpx
import numpy as np

from revival.config import get_settings

_http: httpx.Client | None = None


def _get_http() -> httpx.Client:
    global _http
    if _http is None:
        settings = get_settings()
        _http = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=60,
        )
    return _http


def _call_embedding_api(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    resp = _get_http().post(
        "/embeddings",
        json={"input": texts, "model": settings.embedding_model},
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    # Sort by index to guarantee order
    data.sort(key=lambda x: x["index"])
    return [d["embedding"] for d in data]


def embed_documents(texts: list[str]) -> np.ndarray:
    """Embed a batch of document chunks. Returns (n, dim) float32 array."""
    all_embeddings: list[list[float]] = []
    batch_size = 2048  # OpenAI supports up to 2048 inputs per call
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        all_embeddings.extend(_call_embedding_api(batch))
    return np.array(all_embeddings, dtype=np.float32)


def embed_query(text: str) -> np.ndarray:
    """Embed a single query. Returns (dim,) float32 array."""
    result = _call_embedding_api([text])
    return np.array(result[0], dtype=np.float32)
