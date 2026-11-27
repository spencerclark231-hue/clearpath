"""Run the evaluation set (tests/test_questions.json) through the full pipeline.

For every question it records: retrieval result, whether the expected document
was retrieved, whether it was cited, whether key facts appear in the answer,
whether irrelevant questions were correctly rejected, and timings.
Writes tests/TEST_REPORT.md and tests/test_results.csv.

    python scripts/run_tests.py

Cost: about 13 short chat completions + 13 query embeddings (a few cents at most).
"""
from __future__ import annotations

import csv
import json
import statistics as st
from datetime import datetime

from _common import ROOT, client, persist_dir

from rag import config
from rag.pipeline import answer_question
from rag.vectorstore import ensure_index


def main() -> None:
    oc = client()
    col, rep = ensure_index(oc, persist_dir=persist_dir())
    tests = json.loads((ROOT / "tests" / "test_questions.json").read_text())
    results = []
    for t in tests:
        a = answer_question(col, oc, t["question"], history=[])
        used_docs = [h.meta["doc_code"] for h in a.used]
        cited_docs = [a.used[i - 1].meta["doc_code"] for i in a.cited] if a.status == "answered" else []
        exp = set(t["expected_docs"])
        irrelevant = t["category"].startswith("irrelevant")
        if irrelevant:
            retrieved_ok = "n/a"
            cited_ok = "n/a"
            facts_ok = "n/a"
            rejected_ok = "YES" if a.status == "fallback" else "NO"
        else:
            retrieved_ok = "YES" if exp & set(used_docs) else "NO"
            cited_ok = "YES" if exp & set(cited_docs) else ("n/a (fallback)" if a.status != "answered" else "NO")
            missing = [f for f in t["key_facts"] if f.lower() not in a.raw.lower()]
            facts_ok = "n/a" if not t["key_facts"] else ("YES" if not missing else f"PARTIAL (missing: {', '.join(missing)})")
            rejected_ok = "n/a" if t["category"] == "vague" else ("YES" if a.status == "answered" else "NO (wrongly rejected)")
        results.append({
            "id": t["id"], "category": t["category"], "question": t["question"], "status": a.status,
            "best_distance": f"{a.best_distance:.3f}" if a.best_distance is not None else "",
            "chunks_used": len(a.used), "docs_retrieved": " ".join(dict.fromkeys(used_docs)),
            "docs_cited": " ".join(dict.fromkeys(cited_docs)), "retrieved_correct": retrieved_ok,
            "cited_correct_source": cited_ok, "key_facts_in_answer": facts_ok, "handled_correctly": rejected_ok,
            "total_ms": f"{a.timings.get('total_ms', 0):.0f}", "embed_ms": f"{a.timings.get('embed_ms', 0):.0f}",
            "search_ms": f"{a.timings.get('search_ms', 0):.1f}", "generate_ms": f"{a.timings.get('generate_ms', 0):.0f}",
            "answer": a.raw.replace("\n", " ")})
        print(f"{t['id']} {t['category']:<20} {a.status:<9} d={results[-1]['best_distance']} cited={results[-1]['docs_cited']}")

    with open(ROOT / "tests" / "test_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)

    scored = [r for r in results if r["category"] != "vague"]
    ok = sum(1 for r in scored if r["handled_correctly"] == "YES")
    times = [float(r["total_ms"]) for r in results]
    answered = [float(r["generate_ms"]) for r in results if r["status"] == "answered"]
    md = [f"# CLEARPATH evaluation report - {datetime.now():%Y-%m-%d %H:%M}", "",
          f"Provider `{config.LLM_PROVIDER}` · embeddings `{config.EMBEDDING_MODEL}`, LLM `{config.CHAT_MODEL}` · "
          f"Top-K {config.TOP_K} · gate ≤ {config.RELEVANCE_THRESHOLD} cosine distance · "
          f"index: {rep.chunks} chunks ({rep.status})", "",
          f"**Handled correctly: {ok}/{len(scored)}** (answered when answerable, rejected when irrelevant; vague questions excluded from the score).",
          f"Median total response time: {st.median(times):.0f} ms · median query-embedding time: "
          f"{st.median(float(r['embed_ms']) for r in results):.0f} ms · median search time: "
          f"{st.median(float(r['search_ms']) for r in results):.1f} ms · median generation time (answered only): "
          f"{st.median(answered) if answered else 0:.0f} ms", "",
          "| ID | Category | Question | Status | Best dist. | Retrieved correct | Correct source cited | Key facts | Handled correctly |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        md.append(f"| {r['id']} | {r['category']} | {r['question']} | {r['status']} | {r['best_distance']} | "
                  f"{r['retrieved_correct']} | {r['cited_correct_source']} | {r['key_facts_in_answer']} | {r['handled_correctly']} |")
    md += ["", "## Answers", ""]
    for r in results:
        md += [f"### {r['id']} · {r['category']}", f"**Q:** {r['question']}", "",
               f"**Sources cited:** {r['docs_cited'] or '-'} · **best distance:** {r['best_distance']}", "",
               f"> {r['answer']}", "", "Manual accuracy check (compare with the cited pages): ☐ accurate ☐ partly ☐ wrong", ""]
    (ROOT / "tests" / "TEST_REPORT.md").write_text("\n".join(md))
    print(f"\n{ok}/{len(scored)} handled correctly · wrote tests/TEST_REPORT.md and tests/test_results.csv")


if __name__ == "__main__":
    main()
