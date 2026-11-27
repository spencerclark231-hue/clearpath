"""Shared helpers for the command-line scripts."""
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if not key and secrets.exists():
        key = tomllib.loads(secrets.read_text()).get("OPENAI_API_KEY")
    if not key or "your-key" in key:
        sys.exit("OPENAI_API_KEY not found. Put it in .streamlit/secrets.toml or export it as an environment variable.")
    return key


def client():
    if os.environ.get("CLEARPATH_FAKE_LLM") == "1":
        from tests.fake_openai import FakeOpenAI
        return FakeOpenAI()
    from rag.config import LLM_PROVIDER
    from rag.embedder import make_client
    return make_client() if LLM_PROVIDER == "ollama" else make_client(api_key())


def persist_dir():
    from rag import config
    return ROOT / "chroma_db_offline" if os.environ.get("CLEARPATH_FAKE_LLM") == "1" else config.CHROMA_DIR
