"""Offline stand-in for the OpenAI client - FOR TESTS AND UI PREVIEW ONLY.

Lets the full pipeline (ChromaDB, threshold gate, citations, UI) run without an
API key or network. Embeddings are hashed bag-of-words vectors, so distances are
NOT comparable to text-embedding-3-small; never use this for calibration.
Activated in the app only when the environment variable CLEARPATH_FAKE_LLM=1.
"""
from __future__ import annotations

import hashlib
import math
import re
from types import SimpleNamespace

DIM = 512
_STOP = set("the a an of and or to in on for is are was were be by with at from as that this what which how does do "
            "did it its about into than then there their our we you i me my your".split())


def _tokens(text: str) -> list[str]:
    return [w[:6] for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1]


def fake_embed(text: str) -> list[float]:
    v = [0.0] * DIM
    for t in _tokens(text):
        h = int(hashlib.md5(t.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0 if (h >> 9) & 1 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class _Embeddings:
    def create(self, model: str, input: list[str]):
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=fake_embed(t)) for i, t in enumerate(input)])


class _Completions:
    def create(self, model: str, messages: list[dict], **kw):
        user = messages[-1]["content"]
        q = user.split("QUESTION:", 1)[-1].split("\n\n", 1)[0]
        excerpts = re.findall(r"\[S(\d+)\][^\n]*\n(.+?)(?=\n\n\[S\d+\]|\n\n---)", user, re.S)
        qt = set(_tokens(q))
        best = [(len(qt & set(_tokens(body))), n, body) for n, body in excerpts]
        best.sort(reverse=True)
        if not best or best[0][0] == 0:
            text = "INSUFFICIENT_CONTEXT"
        else:
            _, n, body = best[0]
            sents = re.split(r"(?<=[.!?])\s+", body.replace("\n", " "))
            lead = " ".join(sents[:2])
            text = f"{lead} [S{n}]"
            if len(best) > 1 and best[1][0] > 0:
                _, n2, b2 = best[1]
                text += f"\n\n- {re.split(r'(?<=[.!?])\s+', b2.replace(chr(10), ' '))[0]} [S{n2}]"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


class FakeOpenAI:
    def __init__(self, *a, **k):
        self.embeddings = _Embeddings()
        self.chat = SimpleNamespace(completions=_Completions())
