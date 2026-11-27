"""Stage 3 - Chunking.

Strategy (structure-aware, page-bounded, with overlap):

1. Work page by page so every chunk maps to exactly ONE page -> page citations
   are always correct.
2. Split each page into natural blocks (headings, paragraphs, bullet rows) and
   pack whole blocks into a chunk of up to CHUNK_SIZE characters. Data rows and
   paragraphs are never cut in half unless a single block is itself longer than
   CHUNK_SIZE (then it is split on sentence boundaries).
3. Carry CHUNK_OVERLAP characters (whole sentences) from the end of one chunk
   into the start of the next, so a fact that straddles a boundary is still
   retrievable with its context.
4. Track the current section heading (carried across pages) and prepend a short
   context header "[SCI-05 | Title | Section]" to every chunk. The header is
   embedded with the text, which helps retrieval for questions that name a
   document or topic but not the exact wording of the passage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .cleaner import is_heading
from .config import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARS
from .loader import Page

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9$(\-])")


@dataclass
class Chunk:
    chunk_id: str
    text: str            # context header + body (what is embedded and shown to the LLM)
    body: str            # body only (shown in the source viewer)
    source: str
    doc_code: str
    title: str
    page: int
    section: str
    chunk_index: int

    def metadata(self) -> dict:
        return {"source": self.source, "doc_code": self.doc_code, "title": self.title,
                "page": self.page, "section": self.section, "chunk_index": self.chunk_index,
                "chunk_id": self.chunk_id, "char_count": len(self.body)}


def _blocks(text: str) -> list[str]:
    return [b.strip() for b in text.split("\n") if b.strip()]


def _split_long(block: str, size: int) -> list[str]:
    sents, parts, cur = _SENT_SPLIT.split(block), [], ""
    for s in sents:
        if len(cur) + len(s) + 1 > size and cur:
            parts.append(cur.strip())
            cur = ""
        while len(s) > size:                       # pathological: no sentence breaks
            parts.append(s[:size])
            s = s[size:]
        cur += " " + s
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _overlap_tail(text: str, n: int) -> str:
    if n <= 0:
        return ""
    sents = _SENT_SPLIT.split(text)
    tail = ""
    for s in reversed(sents):
        if len(tail) + len(s) > n and tail:
            break
        tail = (s + " " + tail).strip()
    return tail if len(tail) <= n * 2 else text[-n:]


def chunk_pages(pages: list[Page], size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    chunks: list[Chunk] = []
    section_by_doc: dict[str, str] = {}
    for p in pages:
        section = section_by_doc.get(p.source, "Overview")
        idx = 0
        cur: list[str] = []
        cur_len = 0
        cur_section = section

        def emit(parts: list[str], sec: str):
            nonlocal idx
            body = "\n".join(parts).strip()
            if len(body) < MIN_CHUNK_CHARS:
                return
            idx += 1
            cid = f"{p.doc_code}_{p.page:03d}_{idx:02d}"
            header = f"[{p.doc_code} | {p.title} | {sec}]"
            chunks.append(Chunk(cid, f"{header}\n{body}", body, p.source, p.doc_code, p.title,
                                p.page, sec, idx))

        for block in _blocks(p.text):
            if is_heading(block):
                section = block.strip().rstrip(":")
                # start a fresh chunk at a new section if the current one is reasonably full
                if cur_len > size * 0.5:
                    emit(cur, cur_section)
                    cur, cur_len = [], 0
                if not cur:
                    cur_section = section
                cur.append(block)
                cur_len += len(block) + 1
                continue
            pieces = _split_long(block, size) if len(block) > size else [block]
            for piece in pieces:
                if cur_len + len(piece) + 1 > size and cur:
                    # never leave a heading dangling at the end of a chunk:
                    # it moves forward and opens the next chunk instead
                    heads = []
                    while cur and is_heading(cur[-1]):
                        heads.insert(0, cur.pop())
                    prev = "\n".join(cur)
                    emit(cur, cur_section)
                    if heads:
                        cur = heads                      # new section: no overlap needed
                    else:
                        tail = _overlap_tail(prev, overlap)
                        cur = [tail] if tail else []
                    cur_len = sum(len(x) + 1 for x in cur)
                    cur_section = section
                cur.append(piece)
                cur_len += len(piece) + 1
        emit(cur, cur_section)
        section_by_doc[p.source] = section
    return chunks
