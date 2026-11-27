"""Stage 2 - Text cleaning.

Raw PDF extraction is noisy: running headers and footers repeat on every page,
"Page X of Y" lines interrupt paragraphs, bullet glyphs come out as control
characters, lines are hard-wrapped mid-sentence and words are hyphenated across
line breaks. Embedding that noise wastes tokens and pulls unrelated chunks
together (every chunk would share the same header), so we strip it first.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from .loader import Page

# Explicit patterns for known boilerplate.
_NOISE_PATTERNS = [
    re.compile(r"^\s*page\s+\d+\s*(of\s+\d+)?\s*$", re.I),                 # Page 3 of 7
    re.compile(r"^\s*-?\s*\d{1,3}\s*-?\s*$"),                               # bare page numbers
    re.compile(r"^\s*CLEARPATH KNOWLEDGE BASE\b.*$", re.I),                  # running header
    re.compile(r"^\s*Compiled \d{1,2} \w+ \d{4}.*Internal reference document\s*$", re.I),  # footer
    re.compile(r"^\s*\[SCI-\d+\]\s+Compiled.*$", re.I),                      # txt footer
    re.compile(r"^\s*[=\-_]{5,}\s*$"),                                       # ===== rules
]
_BULLET_CHARS = "\x7f•●▪‣⁃"
_HEADING_RE = re.compile(r"^(\d+\.\s+[A-Z][^.]{2,90}|[A-Z0-9][A-Z0-9 ,&()'/\-]{6,90})$")
_SENTENCE_END = re.compile(r"[.:;!?)\"]$")


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for ch in _BULLET_CHARS:
        text = text.replace(ch, "\n- ")
    text = text.replace(" ", " ").replace("\t", " ")
    # drop remaining control characters except newlines
    return "".join(c for c in text if c == "\n" or unicodedata.category(c)[0] != "C")


def _repeated_lines(pages: list[Page]) -> set[str]:
    """Lines that appear on most pages of a multi-page document = header/footer."""
    if len(pages) < 2:
        return set()
    counts = Counter()
    for p in pages:
        counts.update({ln.strip() for ln in p.text.splitlines() if ln.strip()})
    limit = max(2, int(0.6 * len(pages)))
    return {ln for ln, n in counts.items() if n >= limit}


def is_heading(line: str) -> bool:
    return bool(_HEADING_RE.match(line.strip())) and not line.strip().startswith("- ")


def _rejoin_lines(lines: list[str]) -> list[str]:
    """Merge hard-wrapped lines back into paragraphs; keep headings and bullets separate."""
    out: list[str] = []
    for ln in lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            if out and out[-1] != "":
                out.append("")
            continue
        starts_block = ln.startswith("- ") or is_heading(ln)
        if out and out[-1] and not starts_block and not is_heading(out[-1]):
            prev = out[-1]
            if prev.endswith("-") and ln[:1].islower():          # hyphenated word split
                out[-1] = prev[:-1] + ln
                continue
            if not _SENTENCE_END.search(prev) or ln[:1].islower() or ln[:1].isdigit():
                out[-1] = prev + " " + ln                          # broken sentence
                continue
        out.append(ln)
    return out


def clean_document_pages(pages: list[Page]) -> list[Page]:
    """Clean all pages belonging to ONE document. Returns new Page objects."""
    repeated = _repeated_lines(pages)
    cleaned: list[Page] = []
    for p in pages:
        text = _normalize(p.text)
        kept = []
        for ln in text.splitlines():
            s = ln.strip()
            if s in repeated or any(pat.match(s) for pat in _NOISE_PATTERNS):
                continue
            kept.append(ln)
        lines = _rejoin_lines(kept)
        body = "\n".join(lines)
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"[ ]{2,}", " ", body).strip()
        cleaned.append(Page(p.source, p.doc_code, p.title, p.page, body))
    return cleaned


def clean_pages(pages: list[Page]) -> list[Page]:
    by_doc: dict[str, list[Page]] = {}
    for p in pages:
        by_doc.setdefault(p.source, []).append(p)
    out: list[Page] = []
    for doc_pages in by_doc.values():
        out.extend(clean_document_pages(doc_pages))
    return out
