"""Stages 6-7 - Semantic search, Top-K retrieval and relevance filtering.

ChromaDB returns cosine DISTANCE (0 = same meaning, 1 = unrelated). We never
assume the first hit is trustworthy: every hit is graded into a relevance tier,
and generation only happens if the best hit clears RELEVANCE_THRESHOLD.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .config import MAX_CONTEXT_CHUNKS, POTENTIAL_MAX, RELEVANCE_THRESHOLD, STRONG_MAX, TOP_K
from .embedder import embed_query

# A question is treated as a follow-up only if it refers back to something
# ("what about...", "and the Red Sea?", "how does that compare", "is it...").
# Standalone short questions are NOT merged - otherwise an off-topic question
# asked after a good one would inherit the previous query and slip past the gate.
_FOLLOW_UP = re.compile(r"^(and|also|what about|how about|compared|same for|then)\b|"
                        r"\b(it|its|that|this|those|these|they|them|there|same|above|previous|earlier)\b", re.I)


@dataclass
class Hit:
    chunk_id: str
    text: str
    body: str
    meta: dict
    distance: float
    tier: str

    @property
    def similarity(self) -> float:
        return round(1 - self.distance, 4)


@dataclass
class Retrieval:
    query: str
    hits: list[Hit] = field(default_factory=list)       # all Top-K hits, graded
    used: list[Hit] = field(default_factory=list)       # hits that passed the threshold
    passed: bool = False
    best_distance: float | None = None
    embed_ms: float = 0.0
    search_ms: float = 0.0


def tier_for(distance: float, strong: float = STRONG_MAX, potential: float = POTENTIAL_MAX,
             threshold: float = RELEVANCE_THRESHOLD) -> str:
    if distance <= strong:
        return "strong"
    if distance <= potential:
        return "potential"
    if distance <= threshold:
        return "weak"
    return "irrelevant"


def build_search_query(question: str, history: list[dict]) -> str:
    """Make short follow-ups ('what about the Red Sea?') retrievable by adding the previous question."""
    q = question.strip()
    prev_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
    if prev_user and _FOLLOW_UP.search(q):
        return f"{prev_user} {q}"
    return q


def body_from_document(doc: str) -> str:
    return doc.split("\n", 1)[1] if doc.startswith("[") and "\n" in doc else doc


def retrieve(collection, openai_client, query: str, top_k: int = TOP_K,
             threshold: float = RELEVANCE_THRESHOLD) -> Retrieval:
    r = Retrieval(query=query)
    vec, r.embed_ms = embed_query(openai_client, query)
    t0 = time.perf_counter()
    res = collection.query(query_embeddings=[vec], n_results=top_k,
                           include=["documents", "metadatas", "distances"])
    r.search_ms = (time.perf_counter() - t0) * 1000

    for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]):
        r.hits.append(Hit(cid, doc, body_from_document(doc), meta, float(dist),
                          tier_for(float(dist), threshold=max(threshold, POTENTIAL_MAX))))
    if r.hits:
        r.best_distance = r.hits[0].distance
        r.used = [h for h in r.hits if h.distance <= threshold][:MAX_CONTEXT_CHUNKS]
        r.passed = bool(r.used)
    return r
