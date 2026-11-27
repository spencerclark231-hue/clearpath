"""HTML building blocks for the CLEARPATH interface."""
from __future__ import annotations

import html
from datetime import datetime

from rag.generator import plain_citation
from rag.pipeline import Answer

from .theme import hero_svg

DOC_SHORT = {
    "SCI-01": "Chokepoint Traffic Monitor", "SCI-02": "Hormuz Crisis Brief", "SCI-03": "Red Sea & Suez Brief",
    "SCI-04": "Panama Canal Operations", "SCI-05": "War-Risk Insurance Bulletin", "SCI-06": "JWC Listed Areas Register",
    "SCI-07": "Container Freight Rates", "SCI-08": "Bunker & Energy Bulletin", "SCI-09": "Supply Chain Pressure (GSCPI)",
    "SCI-10": "Country Logistics Scorecard", "SCI-11": "Risk Playbook",
}

e = html.escape


def hero() -> str:
    return f"""
<div class="cp-hero">{hero_svg()}
  <div class="cp-hero-copy">
    <div class="cp-kicker"><b>■</b>&nbsp; Supply chain intelligence &nbsp;//&nbsp; retrieval-augmented analyst</div>
    <div class="cp-title">Clear<span>path</span></div>
    <div class="cp-lede">Grounded answers on chokepoints, war-risk insurance, canal fees, freight and fuel costs,
    built only from a curated knowledge base. Every answer cites its source.</div>
  </div>
</div>
<div class="cp-spec">
  <div><div class="k">Purpose</div><div class="v">Risk and cost answers on shipping disruption for logistics, procurement and
  finance questions.</div></div>
  <div><div class="k">Knowledge base</div><div class="v">11 documents (9 PDF, 2 TXT): market data reports, crisis briefs
  and a risk playbook.</div></div>
  <div><div class="k">Data sources</div><div class="v">IMF PortWatch, World Bank LPI, Drewry WCI, NY Fed GSCPI, JWC, Marsh, EIA.</div></div>
  <div><div class="k">Data as of</div><div class="v">22–26 Nov 2026.</div></div>
</div>"""


def hero_compact() -> str:
    return ('<div class="cp-bar"><div class="cp-title">Clear<span>path</span></div>'
            '<div class="cp-kicker"><b>■</b>&nbsp; Data as of 22–26 Nov 2026</div></div>')


def label(text: str) -> str:
    return f'<div class="cp-label"><i></i>{e(text)}</div>'


def user_message(text: str, ts: str) -> str:
    return (f'<div class="cp-msg-head"><span><b>Query</b> &nbsp;/&nbsp; analyst desk</span><span>{e(ts)}</span></div>'
            f'<div class="cp-q">{e(text)}</div>')


def answer_header(a: Answer, ts: str) -> str:
    state = {"answered": "Grounded analysis", "fallback": "No grounded answer", "error": "System notice"}[a.status]
    return f'<div class="cp-msg-head"><span><b>Clearpath</b> &nbsp;/&nbsp; {state}</span><span>{e(ts)}</span></div>'


def answer_open(a: Answer) -> str:
    cls = {"answered": "", "fallback": "fallback", "error": "error"}[a.status]
    return f'<div class="cp-a {cls}"><div class="cp-a-body">'


def answer_close(a: Answer) -> str:
    foot = ""
    if a.status == "answered":
        docs = []
        for i in a.cited:
            h = a.used[i - 1]
            docs.append(f"<span>S{i}</span> {e(plain_citation(h))}")
        best = f"{1 - a.best_distance:.2f}" if a.best_distance is not None else "–"
        t = a.timings
        foot = (f'<div class="cp-srcline">{"<br>".join(docs)}</div>'
                f'<div class="cp-a-foot"><span>Sources <b>{len(a.cited)}</b></span><span>Top similarity <b>{best}</b></span>'
                f'<span>Total <b>{t.get("total_ms", 0) / 1000:.1f} s</b></span></div>')
    elif a.status == "fallback":
        best = f"{a.best_distance:.3f}" if a.best_distance is not None else "–"
        foot = (f'<div class="cp-a-foot"><span>Relevance gate <b>closed</b></span><span>Best distance <b>{best}</b></span>'
                f'<span>Generation <b>skipped</b></span></div>' if "threshold" in a.fallback_reason else
                f'<div class="cp-a-foot"><span>Relevance gate <b>open</b></span><span>Model verdict <b>insufficient evidence</b></span></div>')
    return f"</div>{foot}</div>"


def _meter(similarity: float, tier: str) -> str:
    w = max(2, min(100, similarity * 100))
    return (f'<div class="cp-meter"><span>Similarity {similarity:.3f}</span><span class="bar"><i style="width:{w:.0f}%"></i></span>'
            f'<span class="tier-{tier}">{tier}</span></div>')


def source_card(i: int, h) -> str:
    m = h.meta
    return f"""
<div class="cp-src"><div class="cp-src-code"><div class="c">{e(str(m.get('doc_code', '')).replace('SCI-', ''))}</div>
<div class="s">SCI · P.{m.get('page')}</div><div class="s" style="color:var(--red)">S{i}</div></div>
<div class="cp-src-main"><div class="cp-src-title">{e(str(m.get('title')))}</div>
<div class="cp-src-meta">{e(str(m.get('source')))} &nbsp;·&nbsp; page {m.get('page')} &nbsp;·&nbsp; {e(str(m.get('section')))} &nbsp;·&nbsp; chunk {e(h.chunk_id)}</div>
<div class="cp-src-text">{e(h.body)}</div>{_meter(h.similarity, h.tier)}</div></div>"""


def retrieval_table(a: Answer, threshold: float) -> str:
    used_ids = {h.chunk_id for h in a.used}
    rows = []
    for rank, h in enumerate(a.all_hits, 1):
        ok = h.chunk_id in used_ids
        rows.append(f'<tr class="{"" if ok else "rej"}"><td>{rank}</td><td>{e(h.chunk_id)}</td>'
                    f'<td>{e(DOC_SHORT.get(h.meta.get("doc_code"), h.meta.get("title", "")))}</td>'
                    f'<td>{h.distance:.3f}</td><td>{h.similarity:.3f}</td><td>{h.tier}</td>'
                    f'<td>{"sent to model" if ok else "rejected"}</td></tr>')
    return (f'<table class="cp-table"><tr><th>#</th><th>Chunk</th><th>Document</th><th>Distance</th><th>Similarity</th>'
            f'<th>Tier</th><th>Decision</th></tr>{"".join(rows)}</table>'
            f'<div class="cp-src-meta" style="margin-top:10px">Cosine distance · gate ≤ {threshold:.2f} · '
            f'search query: “{e(a.search_query)}”</div>')


def sidebar_header() -> str:
    return ('<div class="cp-side-mark">CLEARPATH<i></i></div>'
            '<div class="cp-side-sub">Supply chain intelligence · v1.0</div>')


def sidebar_stats(docs: int, chunks: int, status: str, dims: int) -> str:
    st_txt = {"reused": "Index loaded from disk", "built": "Index built this session", "empty": "Index empty"}.get(status, status)
    return (f'<div class="cp-stat"><div><div class="n">{docs}</div><div class="l">Documents</div></div>'
            f'<div><div class="n">{chunks}</div><div class="l">Chunks</div></div>'
            f'<div><div class="n">{dims}</div><div class="l">Dims</div></div></div>'
            f'<div class="cp-state"><span class="dot"></span>{e(st_txt)} · ChromaDB persistent</div>')


def sidebar_docs(files: list[str]) -> str:
    out = []
    for f in files:
        code = f.split("_")[0]
        out.append(f'<div class="cp-doc"><div class="c">{e(code)}</div><div><div class="t">{e(DOC_SHORT.get(code, f))}</div>'
                   f'<div class="f">{e(f.rsplit(".", 1)[-1])} document</div></div></div>')
    return "".join(out)


def notice(title: str, body_html: str) -> str:
    return f'<div class="cp-notice"><h4>{e(title)}</h4>{body_html}</div>'


def now() -> str:
    return datetime.now().strftime("%H:%M · %d %b").upper()
