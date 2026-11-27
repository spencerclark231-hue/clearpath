"""Build (or verify) the persistent ChromaDB index from the command line.

    python scripts/ingest.py            # build only if documents changed
    python scripts/ingest.py --force    # rebuild from scratch

Committing the resulting chroma_db/ folder lets the deployed app start without
re-embedding anything.
"""
from __future__ import annotations

import sys

from _common import client, persist_dir

from rag.vectorstore import ensure_index


def main() -> None:
    force = "--force" in sys.argv
    col, rep = ensure_index(client(), persist_dir=persist_dir(), force=force,
                            progress=lambda d, n: print(f"  embedded {d}/{n} chunks"))
    print(f"status={rep.status} documents={rep.documents} chunks={rep.chunks} time={rep.seconds:.1f}s")
    for e in rep.errors:
        print("  load error:", e)


if __name__ == "__main__":
    main()
