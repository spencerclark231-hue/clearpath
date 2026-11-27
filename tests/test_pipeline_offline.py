"""Offline tests: run with `pytest -q`. No API key or network needed."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import config  # noqa: E402
from rag.chunker import chunk_pages  # noqa: E402
from rag.cleaner import clean_pages  # noqa: E402
from rag.generator import cited_indices, render_answer_html  # noqa: E402
from rag.loader import Page, load_documents  # noqa: E402
from rag.pipeline import answer_question  # noqa: E402
from rag.vectorstore import ensure_index  # noqa: E402
from tests.fake_openai import FakeOpenAI  # noqa: E402


class CountingFake(FakeOpenAI):
    def __init__(self):
        super().__init__()
        self.embedded = 0
        inner = self.embeddings.create

        def create(model, input):
            self.embedded += len(input)
            return inner(model=model, input=input)
        self.embeddings.create = create


def test_all_documents_load():
    r = load_documents()
    assert not r.errors
    assert len(r.files_loaded) == 11
    assert {p.source.rsplit(".", 1)[1] for p in r.pages} == {"pdf", "txt"}


def test_bad_files_do_not_crash(tmp_path):
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 this is not really a pdf")
    (tmp_path / "empty.txt").write_text("   ")
    (tmp_path / "ok.txt").write_text("Freight rates rose sharply in 2026 on the transpacific lane.")
    r = load_documents(tmp_path)
    assert len(r.errors) == 2 and r.files_loaded == ["ok.txt"]


def test_missing_folder_reports_error(tmp_path):
    r = load_documents(tmp_path / "nope")
    assert r.errors and not r.pages


def test_cleaning_removes_headers_footers_and_page_numbers():
    pages = clean_pages(load_documents().pages)
    joined = "\n".join(p.text for p in pages)
    assert "CLEARPATH KNOWLEDGE BASE" not in joined
    assert "Internal reference document" not in joined
    assert "Page 1 of" not in joined
    assert "\x7f" not in joined


def test_cleaning_rejoins_broken_lines_and_hyphens():
    p = Page("x.pdf", "SCI-99", "T", 1, "The canal was declared\nclosed after the trans-\nit count fell to zero.\nPage 1 of 3")
    out = clean_pages([p])[0].text
    assert out == "The canal was declared closed after the transit count fell to zero."


def test_chunks_have_unique_ids_metadata_and_bounded_size():
    chunks = chunk_pages(clean_pages(load_documents().pages))
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    for c in chunks:
        assert len(c.body) <= config.CHUNK_SIZE + config.CHUNK_OVERLAP + 50
        md = c.metadata()
        assert md["source"] and md["page"] >= 1 and md["doc_code"].startswith("SCI-")
        assert c.text.startswith(f"[{c.doc_code}")


@pytest.fixture()
def index(tmp_path):
    fake = CountingFake()
    col, rep = ensure_index(fake, persist_dir=tmp_path / "db")
    yield fake, col, rep, tmp_path / "db"
    shutil.rmtree(tmp_path / "db", ignore_errors=True)


def test_index_is_persistent_and_not_rebuilt(index):
    fake, col, rep, db = index
    assert rep.status == "built" and rep.chunks > 50
    first = fake.embedded
    fake2 = CountingFake()
    col2, rep2 = ensure_index(fake2, persist_dir=db)
    assert rep2.status == "reused" and rep2.chunks == rep.chunks
    assert fake2.embedded == 0          # no document re-embedding on restart
    answer_question(col2, fake2, "Hormuz war risk premium", [])
    assert fake2.embedded == 1          # only the query is embedded
    assert first == rep.chunks


def test_irrelevant_question_falls_back(index):
    fake, col, *_ = index
    a = answer_question(col, fake, "What is a good recipe for lasagna?", [])
    assert a.status == "fallback" and a.timings["generate_ms"] == 0
    assert "could not find enough relevant information" in a.raw


def test_relevant_question_is_answered_with_citations(index):
    fake, col, *_ = index
    a = answer_question(col, fake, "Hormuz war-risk insurance premium hull value July 2026", [])
    assert a.status == "answered" and a.cited
    assert any(h.meta["doc_code"] in ("SCI-05", "SCI-02") for h in a.used)


def test_follow_up_only_merges_when_referential(index):
    fake, col, *_ = index
    hist = [{"role": "user", "content": "Hormuz war-risk insurance premium"}]
    assert answer_question(col, fake, "Who won the 2022 FIFA World Cup?", hist).status == "fallback"


def test_citation_rendering_escapes_html_and_drops_fake_sources():
    from rag.retriever import Hit
    h = Hit("SCI-05_002_01", "t", "b", {"doc_code": "SCI-05", "page": 2, "title": "War"}, 0.3, "strong")
    out = render_answer_html("Rates hit 10% <script>x</script> [S1][S7]", [h])
    assert "<script>" not in out and "SCI-05&nbsp;p.2" in out and "S7" not in out
    assert cited_indices("a [S1] b [S2] [S1] [S9]", 2) == [1, 2]
