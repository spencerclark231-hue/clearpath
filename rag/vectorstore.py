"""Stage 5 - Persistent vector database (ChromaDB).

The index is built ONCE and stored on disk in chroma_db/. On every app start we
compute a fingerprint of (document contents + chunking settings + embedding
model). If the stored collection has the same fingerprint, it is reused as-is
and no embeddings are generated. Only when documents or settings change is the
collection rebuilt.

    Embed documents once -> store persistently -> embed only new queries -> search
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from chromadb.config import Settings

from .chunker import chunk_pages
from .cleaner import clean_pages
from .config import (CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME, DOCS_DIR,
                     EMBEDDING_MODEL, SUPPORTED_EXTENSIONS)
from .embedder import embed_texts
from .loader import load_documents


@dataclass
class IndexReport:
    status: str = "unknown"            # "reused" | "built" | "empty"
    documents: int = 0
    chunks: int = 0
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


def kb_fingerprint(docs_dir: Path = DOCS_DIR) -> str:
    h = hashlib.sha256()
    h.update(f"{EMBEDDING_MODEL}|{CHUNK_SIZE}|{CHUNK_OVERLAP}|v1".encode())
    for p in sorted(docs_dir.glob("*")):
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            h.update(p.name.encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def get_client(persist_dir: Path = CHROMA_DIR) -> chromadb.ClientAPI:
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir), settings=Settings(anonymized_telemetry=False))


def _existing(client: chromadb.ClientAPI, name: str):
    try:
        return client.get_collection(name, embedding_function=None)
    except Exception:  # noqa: BLE001 - "does not exist" error type varies by chroma version
        return None


def ensure_index(openai_client, docs_dir: Path = DOCS_DIR, persist_dir: Path = CHROMA_DIR,
                 progress=None, force: bool = False):
    """Return (collection, IndexReport). Builds the index only if needed."""
    t0 = time.perf_counter()
    report = IndexReport()
    fp = kb_fingerprint(docs_dir)
    client = get_client(persist_dir)
    col = _existing(client, COLLECTION_NAME)

    if col is not None and not force and col.count() > 0 and (col.metadata or {}).get("kb_fingerprint") == fp:
        meta = col.metadata or {}
        report.status, report.chunks = "reused", col.count()
        report.documents = int(meta.get("documents", 0))
        report.files = [f for f in str(meta.get("files", "")).split("|") if f]
        report.errors = [x for x in str(meta.get("load_errors", "")).split(" || ") if x]
        report.seconds = time.perf_counter() - t0
        return col, report

    # ---- (re)build ---------------------------------------------------------
    loaded = load_documents(docs_dir)
    report.errors = loaded.errors
    report.files = loaded.files_loaded
    chunks = chunk_pages(clean_pages(loaded.pages))
    if not chunks:
        report.status = "empty"
        report.seconds = time.perf_counter() - t0
        return None, report

    vectors = embed_texts(openai_client, [c.text for c in chunks], progress=progress)

    if col is not None:
        client.delete_collection(COLLECTION_NAME)
    col = client.create_collection(
        COLLECTION_NAME, embedding_function=None,
        metadata={"hnsw:space": "cosine", "kb_fingerprint": fp, "embedding_model": EMBEDDING_MODEL,
                  "documents": len(loaded.files_loaded), "files": "|".join(loaded.files_loaded),
                  "load_errors": " || ".join(loaded.errors)},
    )
    for i in range(0, len(chunks), 200):
        part = chunks[i:i + 200]
        col.add(ids=[c.chunk_id for c in part], embeddings=vectors[i:i + 200],
                documents=[c.text for c in part], metadatas=[c.metadata() for c in part])

    report.status, report.chunks, report.documents = "built", col.count(), len(loaded.files_loaded)
    report.seconds = time.perf_counter() - t0
    return col, report
