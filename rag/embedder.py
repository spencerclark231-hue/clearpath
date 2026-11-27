"""Stage 4 - Embeddings.

One embedding model (config.EMBEDDING_MODEL) is used for BOTH document chunks
and user questions; mixing models would put vectors in different spaces and
make distances meaningless. Both providers go through the OpenAI SDK: Ollama
serves the same /v1 endpoints on localhost.
"""
from __future__ import annotations

import time

from openai import OpenAI

from .config import EMBED_BATCH_SIZE, EMBEDDING_MODEL, LLM_PROVIDER, OLLAMA_BASE_URL


def make_client(api_key: str | None = None) -> OpenAI:
    if LLM_PROVIDER == "ollama":
        # Ollama ignores the key but the SDK requires one. Local generation and the
        # first model load take longer than an API call, hence the longer timeout.
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=180, max_retries=1)
    return OpenAI(api_key=api_key, timeout=45, max_retries=2)


def embed_texts(client: OpenAI, texts: list[str], model: str = EMBEDDING_MODEL,
                batch_size: int = EMBED_BATCH_SIZE, progress=None) -> list[list[float]]:
    """Embed many texts in batches (used once, at index-build time)."""
    vectors: list[list[float]] = []
    total = len(texts)
    for start in range(0, total, batch_size):
        batch = [t.replace("\n", " ") for t in texts[start:start + batch_size]]
        resp = client.embeddings.create(model=model, input=batch)
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        if progress:
            progress(min(start + batch_size, total), total)
    return vectors


def embed_query(client: OpenAI, text: str, model: str = EMBEDDING_MODEL) -> tuple[list[float], float]:
    """Embed a single question. Returns (vector, milliseconds)."""
    t0 = time.perf_counter()
    resp = client.embeddings.create(model=model, input=[text.replace("\n", " ")])
    return resp.data[0].embedding, (time.perf_counter() - t0) * 1000
