"""Stage 1 - Document loading.

Extracts raw text page-by-page from PDF and TXT files. A single bad file never
crashes ingestion: failures are collected and reported back to the UI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .config import DOCS_DIR, SUPPORTED_EXTENSIONS


@dataclass
class Page:
    source: str          # file name, e.g. SCI-05_Marine_War_Risk....pdf
    doc_code: str        # e.g. SCI-05
    title: str           # human readable document title
    page: int            # 1-based page number
    text: str            # raw extracted text


@dataclass
class LoadResult:
    pages: list[Page] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files_loaded: list[str] = field(default_factory=list)


def _doc_code(path: Path) -> str:
    m = re.match(r"(SCI-\d+)", path.stem)
    return m.group(1) if m else path.stem[:12]


def _title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 12 and not line.upper().startswith("CLEARPATH KNOWLEDGE BASE"):
            return line.title() if line.isupper() else line
    return fallback


def _load_pdf(path: Path) -> list[Page]:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError("PDF is encrypted")
    texts = [(p.extract_text() or "") for p in reader.pages]
    if not any(t.strip() for t in texts):
        raise ValueError("no extractable text (scanned image PDF?)")
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else None) \
        or _title_from_text(texts[0], path.stem)
    return [Page(path.name, _doc_code(path), title, i + 1, t) for i, t in enumerate(texts)]


def _load_txt(path: Path) -> list[Page]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise ValueError("file is empty")
    return [Page(path.name, _doc_code(path), _title_from_text(text, path.stem), 1, text)]


def load_documents(docs_dir: Path = DOCS_DIR) -> LoadResult:
    result = LoadResult()
    if not docs_dir.exists():
        result.errors.append(f"Documents folder not found: {docs_dir}")
        return result
    files = sorted(p for p in docs_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        result.errors.append("No PDF or TXT documents found in the knowledge base folder.")
    for path in files:
        try:
            pages = _load_pdf(path) if path.suffix.lower() == ".pdf" else _load_txt(path)
            result.pages.extend(pages)
            result.files_loaded.append(path.name)
        except (PdfReadError, ValueError, OSError, UnicodeError) as e:
            result.errors.append(f"{path.name}: {e}")
        except Exception as e:  # noqa: BLE001 - never let one file kill ingestion
            result.errors.append(f"{path.name}: unexpected extraction error ({type(e).__name__}: {e})")
    return result
