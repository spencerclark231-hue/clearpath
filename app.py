"""CLEARPATH - Supply Chain Intelligence (RAG chatbot)

Documents -> Cleaning -> Chunking -> Embeddings -> ChromaDB (persistent) -> Retrieval
-> Relevance filtering -> Grounded generation -> Citations -> Streamlit chat

Run locally:   streamlit run app.py
Secrets:       .streamlit/secrets.toml  ->  OPENAI_API_KEY = "sk-..."
               or LLM_PROVIDER = "ollama" for local models (no key)
"""
from __future__ import annotations

# ChromaDB needs SQLite >= 3.35. Some hosts (incl. older Streamlit Cloud images)
# ship an older system SQLite; swap in the bundled pysqlite3 if it is installed.
try:  # pragma: no cover - environment dependent
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import os

import streamlit as st

from rag import config
from rag.pipeline import Answer, answer_question
from ui import components as ui
from ui.theme import CSS

st.set_page_config(page_title="CLEARPATH · Supply Chain Intelligence", page_icon="◪",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

STARTERS = [
    ("01", "Hormuz", "How much did war-risk insurance for the Strait of Hormuz rise in 2026?"),
    ("02", "Routing", "Can Asia–Europe cargo route through Suez right now under the risk playbook?"),
    ("03", "Freight", "What is the latest Drewry WCI rate from Shanghai to Rotterdam?"),
    ("04", "Panama", "What were the record Panama Canal auction prices in 2026?"),
]


# --------------------------------------------------------------------------- #
# Secrets and clients
# --------------------------------------------------------------------------- #
def get_api_key() -> str | None:
    try:
        key = st.secrets.get("OPENAI_API_KEY")
    except Exception:  # noqa: BLE001 - no secrets.toml at all
        key = None
    key = key or os.environ.get("OPENAI_API_KEY")
    return key.strip() if key and key.strip() and "your-key" not in key else None


FAKE = os.environ.get("CLEARPATH_FAKE_LLM") == "1"   # developer-only offline preview
OLLAMA = config.LLM_PROVIDER == "ollama"             # local models, no key needed


@st.cache_resource(show_spinner=False)
def get_openai(api_key: str):
    if FAKE:
        from tests.fake_openai import FakeOpenAI
        return FakeOpenAI()
    from rag.embedder import make_client
    return make_client(api_key)


def persist_dir():
    return config.ROOT / "chroma_db_offline" if FAKE else config.CHROMA_DIR


@st.cache_resource(show_spinner=False)
def get_index(api_key: str):
    """Load the persistent ChromaDB collection (cached for the server process)."""
    from rag.vectorstore import ensure_index
    return ensure_index(get_openai(api_key), persist_dir=persist_dir())


def index_is_current() -> bool:
    """Cheap check (no API calls): does the stored collection match the documents on disk?"""
    from rag.vectorstore import COLLECTION_NAME, _existing, get_client, kb_fingerprint
    col = _existing(get_client(persist_dir()), COLLECTION_NAME)
    return bool(col and col.count() and (col.metadata or {}).get("kb_fingerprint") == kb_fingerprint())


def friendly_error(exc: Exception) -> tuple[str, str]:
    """Map library exceptions to messages a user can act on."""
    name = type(exc).__name__
    try:
        import openai
        if OLLAMA:
            if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
                return "Ollama not reachable", (f"Nothing answered at <code>{e_(config.OLLAMA_BASE_URL)}</code>. "
                                                "Open the Ollama app (or run <code>ollama serve</code>) and try again.")
            if isinstance(exc, openai.NotFoundError):
                return "Model not installed", (f"Ollama has no <code>{e_(config.EMBEDDING_MODEL)}</code> or "
                                               f"<code>{e_(config.CHAT_MODEL)}</code>. Run <code>ollama pull</code> "
                                               "for the missing model, then retry.")
            if isinstance(exc, openai.APIError):
                return "Ollama error", f"Ollama returned an error ({e_(name)}). Please try again."
        if isinstance(exc, openai.AuthenticationError):
            return "API key rejected", "OpenAI did not accept the configured key. Check <code>OPENAI_API_KEY</code> in your secrets."
        if isinstance(exc, openai.RateLimitError):
            return "Rate limit or quota reached", "OpenAI is throttling requests or the account is out of credit. Wait a moment, or check billing."
        if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
            return "Network problem", "Could not reach the OpenAI API. Check the internet connection and try again."
        if isinstance(exc, openai.BadRequestError):
            return "Request rejected", "OpenAI rejected the request (the question may be too long). Try a shorter question."
        if isinstance(exc, openai.APIError):
            return "OpenAI service error", "The OpenAI API returned an error. Please try again in a moment."
    except ImportError:
        pass
    if "chroma" in type(exc).__module__.lower() or "sqlite" in str(exc).lower():
        return "Vector database error", "ChromaDB could not be read. Delete the <code>chroma_db/</code> folder and restart to rebuild it."
    return "Unexpected error", f"Something went wrong ({e_(name)}). The conversation is intact; please try again."


def e_(s: str) -> str:
    import html
    return html.escape(str(s))


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def render_answer(a: Answer, ts: str, threshold: float) -> None:
    st.markdown(ui.answer_header(a, ts) + ui.answer_open(a) + a.html + ui.answer_close(a), unsafe_allow_html=True)
    if a.status == "error":
        return
    if a.status == "answered":
        title = f"View sources · {len(a.cited)} cited"
    else:
        title = "Why no answer? · retrieval diagnostics"
    with st.expander(title):
        if a.status == "answered":
            t1, t2, t3 = st.tabs(["Cited sources", f"All retrieved · top {len(a.all_hits)}", "Telemetry"])
            with t1:
                st.markdown("".join(ui.source_card(i, a.used[i - 1]) for i in a.cited), unsafe_allow_html=True)
            with t2:
                st.markdown(ui.retrieval_table(a, threshold), unsafe_allow_html=True)
            with t3:
                t = a.timings
                st.markdown(
                    f'<table class="cp-table"><tr><th>Stage</th><th>Time</th></tr>'
                    f'<tr><td>Query embedding ({config.EMBEDDING_MODEL})</td><td>{t["embed_ms"]:.0f} ms</td></tr>'
                    f'<tr><td>ChromaDB similarity search</td><td>{t["search_ms"]:.1f} ms</td></tr>'
                    f'<tr><td>Grounded generation ({config.CHAT_MODEL})</td><td>{t["generate_ms"]:.0f} ms</td></tr>'
                    f'<tr><td><b>Total response</b></td><td><b>{t["total_ms"]:.0f} ms</b></td></tr></table>'
                    f'<div class="cp-src-meta" style="margin-top:10px">Document embeddings are read from disk; '
                    f'only the question is embedded at query time.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cp-src-meta">{e_(a.fallback_reason)}</div>', unsafe_allow_html=True)
            if a.all_hits:
                st.markdown(ui.retrieval_table(a, threshold), unsafe_allow_html=True)


def render_history(threshold: float) -> None:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "user":
                st.markdown(ui.user_message(m["content"], m["ts"]), unsafe_allow_html=True)
            else:
                render_answer(m["answer"], m["ts"], threshold)


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending" not in st.session_state:
    st.session_state.pending = None

api_key = "ollama" if OLLAMA else get_api_key() or ("offline" if FAKE else None)

# full header on the empty start screen; a slim bar once the conversation starts
st.markdown(ui.hero_compact() if st.session_state.messages else ui.hero(), unsafe_allow_html=True)

# --- missing key: explain and stop (no crash) -------------------------------
if not api_key:
    with st.sidebar:
        st.markdown(ui.sidebar_header(), unsafe_allow_html=True)
    st.markdown(ui.notice("OpenAI API key required", """
<p>CLEARPATH needs an OpenAI API key to embed questions and generate answers. The key is never stored in the code.</p>
<ul><li><b>Local:</b> create <code>.streamlit/secrets.toml</code> containing <code>OPENAI_API_KEY = "sk-..."</code>, then restart.</li>
<li><b>Streamlit Community Cloud:</b> App → Settings → Secrets, paste the same line, save.</li></ul>"""), unsafe_allow_html=True)
    st.stop()

# --- load / build the persistent index --------------------------------------
collection, report = None, None
try:
    if "index_ready" not in st.session_state:
        with st.status("Opening knowledge base…", expanded=False) as status:
            if not index_is_current():
                # first run (or documents changed): embed once, with a visible progress bar
                from rag.vectorstore import ensure_index
                bar = st.progress(0.0, text="Embedding document chunks")
                _, built = ensure_index(get_openai(api_key), persist_dir=persist_dir(),
                                        progress=lambda d, n: bar.progress(d / n, text=f"Embedding chunks {d}/{n}"))
                bar.empty()
                get_index.clear()
            collection, report = get_index(api_key)
            if report.status == "empty":
                status.update(label="Knowledge base is empty", state="error")
            else:
                status.update(label=f"Knowledge base ready · {report.chunks} chunks from {report.documents} documents",
                              state="complete")
        st.session_state.index_ready = True
    else:
        collection, report = get_index(api_key)
except Exception as exc:  # noqa: BLE001
    get_index.clear()
    t, body = friendly_error(exc)
    st.markdown(ui.notice(t, f"<p>{body}</p><p>The knowledge base could not be opened, so questions are disabled.</p>"),
                unsafe_allow_html=True)
    st.stop()

if report.errors:
    st.warning("Some documents could not be loaded and were skipped: " + "; ".join(report.errors))
if collection is None or report.status == "empty":
    st.markdown(ui.notice("Knowledge base is empty",
                          "<p>No readable PDF or TXT documents were found in <code>documents/</code>. "
                          "Add documents and restart the app.</p>"), unsafe_allow_html=True)
    st.stop()

# --- sidebar ------------------------------------------------------------------
with st.sidebar:
    st.markdown(ui.sidebar_header(), unsafe_allow_html=True)
    dims = len(collection.get(limit=1, include=["embeddings"])["embeddings"][0])
    st.markdown(ui.sidebar_stats(report.documents or len(report.files), report.chunks, report.status, dims),
                unsafe_allow_html=True)
    with st.expander(f"Knowledge base · {len(report.files)} documents"):
        st.markdown(ui.sidebar_docs(report.files), unsafe_allow_html=True)
    st.markdown(ui.label("Retrieval controls"), unsafe_allow_html=True)
    with st.expander("Advanced settings"):
        top_k = st.slider("Top-K chunks retrieved", 1, 10, config.TOP_K,
                          help="How many nearest chunks ChromaDB returns for each question.")
        threshold = st.slider("Relevance gate (max cosine distance)", 0.30, 0.90, config.RELEVANCE_THRESHOLD, 0.01,
                              help="Chunks farther than this are rejected. If none pass, CLEARPATH refuses to answer.")
        st.caption(f"Embeddings: {config.EMBEDDING_MODEL} · LLM: {config.CHAT_MODEL} · "
                   f"chunk {config.CHUNK_SIZE} chars / overlap {config.CHUNK_OVERLAP}")
    st.write("")
    if st.button("New briefing", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown('<div class="cp-foot">Market data: public sources, Nov 2026.</div>', unsafe_allow_html=True)

# --- conversation -------------------------------------------------------------
if not st.session_state.messages:
    st.markdown(ui.label("Briefing starters"), unsafe_allow_html=True)
    cols = st.columns(4)
    for col, (idx, tag, q) in zip(cols, STARTERS):
        with col:
            st.markdown(f'<div class="cp-tile-idx"><b>{idx}</b> / {tag.upper()}</div>', unsafe_allow_html=True)
            if st.button(q, key=f"starter_{idx}", use_container_width=True):
                st.session_state.pending = q
                st.rerun()
else:
    st.markdown(ui.label("Briefing log"), unsafe_allow_html=True)

render_history(threshold)

typed = st.chat_input("Ask about chokepoints, war-risk insurance, canal fees, freight, fuel, or the risk playbook…",
                      max_chars=1000)
question = typed if typed is not None else st.session_state.pending
st.session_state.pending = None

if question is not None:
    question = question.strip()
    if not question:
        st.toast("Type a question first: the message was empty.")
    else:
        ts = ui.now()
        # conversational memory: prior questions + grounded answers only (no fallbacks/errors)
        history = [{"role": m["role"], "content": m["content"], "raw": m.get("raw", m["content"])}
                   for m in st.session_state.messages
                   if m["role"] == "user" or m["answer"].status == "answered"]
        with st.chat_message("user"):
            st.markdown(ui.user_message(question, ts), unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": question, "ts": ts})

        with st.chat_message("assistant"):
            with st.spinner("Embedding question · searching knowledge base · drafting grounded answer…"):
                try:
                    a = answer_question(collection, get_openai(api_key), question, history,
                                        top_k=top_k, threshold=threshold)
                except Exception as exc:  # noqa: BLE001
                    t, body = friendly_error(exc)
                    a = Answer(question=question, status="error", raw=t, html=f"<p><b>{e_(t)}.</b> {body}</p>")
            ts_a = ui.now()
            render_answer(a, ts_a, threshold)
        st.session_state.messages.append({"role": "assistant", "content": a.raw, "raw": a.raw, "answer": a, "ts": ts_a})
        if len(st.session_state.messages) == 2:
            st.rerun()   # swap the starter tiles for the briefing-log header
