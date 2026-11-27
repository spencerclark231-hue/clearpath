"""Central configuration for the CLEARPATH RAG pipeline.

Every tunable lives here so the README, the calibration script and the app
all agree on the same values.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "documents"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "clearpath_kb_v1"
SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".md")


def _setting(name: str, default=None):
    """Environment variable first, then .streamlit/secrets.toml, so the app and the scripts agree."""
    if os.environ.get(name):
        return os.environ[name]
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        try:
            value = tomllib.loads(secrets.read_text()).get(name)
        except tomllib.TOMLDecodeError:
            value = None
        if value is not None:
            return str(value)
    return default


# ---- Provider ---------------------------------------------------------------
# "openai": OpenAI API, needs OPENAI_API_KEY.
# "ollama": local models through Ollama's OpenAI-compatible endpoint, no key.
LLM_PROVIDER = str(_setting("LLM_PROVIDER", "openai")).strip().lower()
if LLM_PROVIDER not in ("openai", "ollama"):
    raise ValueError(f"LLM_PROVIDER must be 'openai' or 'ollama', not {LLM_PROVIDER!r}")
OLLAMA_BASE_URL = _setting("OLLAMA_BASE_URL", "http://localhost:11434/v1/")

# ---- Models ---------------------------------------------------------------
# The SAME embedding model is used for document chunks and for user queries.
_MODELS = {
    "openai": ("text-embedding-3-small", "gpt-4o-mini"),
    "ollama": (_setting("OLLAMA_EMBED_MODEL", "nomic-embed-text"), _setting("OLLAMA_CHAT_MODEL", "llama3.1:8b")),
}
EMBEDDING_MODEL, CHAT_MODEL = _MODELS[LLM_PROVIDER]
TEMPERATURE = 0.1          # low: we want faithful, repeatable answers
MAX_ANSWER_TOKENS = 700
EMBED_BATCH_SIZE = 64

# ---- Chunking -------------------------------------------------------------
# ~900 characters is roughly 180-220 tokens: large enough to hold a complete
# data row or a full paragraph of narrative (with its numbers and its source
# attribution), small enough that one chunk is about one idea.
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150        # ~1-2 sentences carried across boundaries
MIN_CHUNK_CHARS = 80       # drop fragments too small to be useful

# ---- Retrieval ------------------------------------------------------------
# nomic-embed-text packs related chunks closer together than text-embedding-3-small,
# so the chunk a question needs often ranks 6th or 7th; Ollama retrieves 7.
TOP_K = 7 if LLM_PROVIDER == "ollama" else 5   # candidates pulled from ChromaDB per question
MAX_CONTEXT_CHUNKS = TOP_K                     # chunks that may be sent to the LLM

# Cosine DISTANCE (0 = identical, 1 = unrelated). Lower is better.
# Bands were chosen with scripts/calibrate_threshold.py (see tests/CALIBRATION.md)
# by probing the knowledge base with direct, paraphrased, vague, misspelled and
# irrelevant questions. Distances depend on the embedding model, so each provider
# has its own bands: (strong max, potential max, relevance threshold).
_BANDS = {
    "openai": (0.45, 0.55, 0.62),
    "ollama": (0.30, 0.36, 0.40),
}
STRONG_MAX, POTENTIAL_MAX, RELEVANCE_THRESHOLD = _BANDS[LLM_PROVIDER]
# STRONG_MAX     <= : strongly relevant
# POTENTIAL_MAX  <= : potentially relevant
# RELEVANCE_THRESHOLD <= : weakly relevant (still usable); > : irrelevant
RELEVANCE_THRESHOLD = float(_setting("RELEVANCE_THRESHOLD", RELEVANCE_THRESHOLD))
if not STRONG_MAX < POTENTIAL_MAX < RELEVANCE_THRESHOLD:
    raise ValueError(f"RELEVANCE_THRESHOLD {RELEVANCE_THRESHOLD} must sit above POTENTIAL_MAX {POTENTIAL_MAX}")
# Gate: generation runs only if the BEST chunk is within RELEVANCE_THRESHOLD.
# Only chunks within RELEVANCE_THRESHOLD are passed to the model.

FALLBACK_MESSAGE = (
    "I could not find enough relevant information in the CLEARPATH knowledge base "
    "to answer that reliably. Try asking about chokepoint traffic, war-risk "
    "insurance, canal fees, freight rates, fuel costs, supply chain pressure, "
    "country logistics scores or the risk playbook."
)
