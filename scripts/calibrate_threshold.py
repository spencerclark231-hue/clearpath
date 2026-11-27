"""Calibrate the relevance threshold against THIS knowledge base.

Embeds a set of probe questions (direct, paraphrased, vague, misspelled and
irrelevant), looks at the best cosine distance each one gets from ChromaDB, and
recommends a gate value that separates answerable from irrelevant questions.
Writes tests/CALIBRATION.md. Cost: ~30 query embeddings (well under one cent).

    python scripts/calibrate_threshold.py
"""
from __future__ import annotations

import statistics as st
from datetime import datetime

from _common import ROOT, client, persist_dir

from rag import config
from rag.retriever import retrieve, tier_for
from rag.vectorstore import ensure_index

PROBES = {
    "direct": [
        "What was the Drewry World Container Index composite rate on 19 November 2026?",
        "How many daily transits is the Panama Canal allowing after its 9 November 2026 advisory?",
        "Which countries were added to the JWC listed areas in circular JWLA-033?",
        "What was the war-risk premium for the Strait of Hormuz on 22 July 2026?",
        "What is Singapore's VLSFO average price in October 2026?",
        "What is Singapore's Logistics Performance Index score?",
    ],
    "paraphrased": [
        "How expensive has it become to insure a ship against war damage when sailing past Iran?",
        "Is there less strain on worldwide supply networks now than there was a month earlier?",
        "How much does it cost to ship a box from China to the US East Coast these days?",
        "Who signs off when insurance for a risky voyage gets very costly?",
        "Which waterway has seen the biggest collapse in ship traffic?",
    ],
    "vague": [
        "What's going on with shipping?",
        "Is it risky right now?",
        "Tell me about canals.",
        "fuel?",
    ],
    "misspelled": [
        "wat hapend to the sues canal toll rebate for big contaner ships",
        "hormuz insurence premuim july",
        "panama canel auction recrod price",
        "drewery world contianer index latest",
    ],
    "irrelevant": [
        "What is a good recipe for lasagna?",
        "Who won the 2022 FIFA World Cup?",
        "How do I fix a flat bicycle tire?",
        "Write me a poem about autumn.",
        "What is the capital of Australia?",
        "Explain how photosynthesis works.",
        "What will the price of Bitcoin be next year?",
        "Recommend a good laptop for gaming.",
    ],
}


def main() -> None:
    oc = client()
    col, rep = ensure_index(oc, persist_dir=persist_dir())
    rows, best = [], {}
    for cat, qs in PROBES.items():
        for q in qs:
            r = retrieve(col, oc, q, top_k=config.TOP_K, threshold=1.0)
            d = r.hits[0].distance if r.hits else 1.0
            best.setdefault(cat, []).append(d)
            top = r.hits[0].meta.get("doc_code") if r.hits else "-"
            rows.append((cat, q, d, top, tier_for(d)))

    answerable = best["direct"] + best["paraphrased"] + best["misspelled"]
    worst_ok = max(answerable)
    best_irrel = min(best["irrelevant"])
    gap = best_irrel - worst_ok
    recommended = round((worst_ok + best_irrel) / 2, 2) if gap > 0 else round(best_irrel - 0.02, 2)

    lines = [f"# Threshold calibration - {datetime.now():%Y-%m-%d %H:%M}", "",
             f"Embedding model: `{config.EMBEDDING_MODEL}` · collection chunks: {rep.chunks} · Top-K: {config.TOP_K}", "",
             "Best (top-1) cosine distance per probe. Lower = more similar.", "",
             "| Category | Probe | Best distance | Top doc | Tier (current bands) |", "|---|---|---|---|---|"]
    lines += [f"| {c} | {q} | {d:.3f} | {t} | {tier} |" for c, q, d, t, tier in rows]
    lines += ["", "## Summary by category", "", "| Category | min | mean | max |", "|---|---|---|---|"]
    for cat, ds in best.items():
        lines.append(f"| {cat} | {min(ds):.3f} | {st.mean(ds):.3f} | {max(ds):.3f} |")
    lines += ["", "## Recommendation", "",
              f"- Worst answerable probe (direct/paraphrased/misspelled): **{worst_ok:.3f}**",
              f"- Closest irrelevant probe: **{best_irrel:.3f}**",
              f"- Separation gap: **{gap:.3f}**",
              f"- Recommended `RELEVANCE_THRESHOLD`: **{recommended:.2f}** (currently {config.RELEVANCE_THRESHOLD:.2f})", "",
              "Vague probes are reported but not used to set the gate: they may legitimately land on either side. "
              "When they pass the gate, the system prompt still forces the model to answer only from the retrieved "
              "chunks or return the fallback (second safety layer).",
              "", "Update `rag/config.py` if the recommendation differs, then re-run `scripts/run_tests.py`."]
    out = ROOT / "tests" / "CALIBRATION.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines[-12:]))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
