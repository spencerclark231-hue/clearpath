"""Orchestrates one question through the query-time pipeline:

question -> query embedding -> semantic search (Top-K) -> distance analysis ->
threshold filter -> grounded prompt -> LLM -> citations
"""
from __future__ import annotations

import html
import time
from dataclasses import dataclass, field

from .config import FALLBACK_MESSAGE, RELEVANCE_THRESHOLD, TOP_K
from .generator import cited_indices, generate, is_no_answer, render_answer_html
from .retriever import Hit, build_search_query, retrieve


@dataclass
class Answer:
    question: str
    status: str                       # "answered" | "fallback" | "error"
    raw: str = ""                     # model text with [S#] markers
    html: str = ""                    # rendered answer
    used: list[Hit] = field(default_factory=list)
    all_hits: list[Hit] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)
    fallback_reason: str = ""
    search_query: str = ""
    best_distance: float | None = None
    timings: dict = field(default_factory=dict)
    error: str = ""


def answer_question(collection, openai_client, question: str, history: list[dict],
                    top_k: int = TOP_K, threshold: float = RELEVANCE_THRESHOLD, model: str | None = None) -> Answer:
    t_start = time.perf_counter()
    search_q = build_search_query(question, history)
    r = retrieve(collection, openai_client, search_q, top_k=top_k, threshold=threshold)
    a = Answer(question=question, status="fallback", all_hits=r.hits, used=r.used,
               search_query=search_q, best_distance=r.best_distance)
    a.timings = {"embed_ms": r.embed_ms, "search_ms": r.search_ms, "generate_ms": 0.0}

    if not r.passed:
        a.fallback_reason = ("No chunks in the knowledge base." if not r.hits else
                             f"Best match distance {r.best_distance:.3f} is above the relevance threshold {threshold:.2f}.")
        a.raw = FALLBACK_MESSAGE
        a.html = f"<p>{html.escape(FALLBACK_MESSAGE)}</p>"
    else:
        kwargs = {"model": model} if model else {}
        text, a.timings["generate_ms"] = generate(openai_client, question, r.used, history, **kwargs)
        if is_no_answer(text):
            a.fallback_reason = "Relevant-looking chunks were found, but the model judged they do not contain the answer."
            a.raw = FALLBACK_MESSAGE
            a.html = f"<p>{html.escape(FALLBACK_MESSAGE)}</p>"
        else:
            a.status = "answered"
            a.raw = text
            a.cited = cited_indices(text, len(r.used)) or list(range(1, len(r.used) + 1))
            a.html = render_answer_html(text, r.used)
    a.timings["total_ms"] = (time.perf_counter() - t_start) * 1000
    return a
