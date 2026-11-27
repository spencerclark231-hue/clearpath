# CLEARPATH: supply chain intelligence on a RAG pipeline

## What it is

CLEARPATH is a retrieval-augmented chatbot for questions about shipping and supply chain risk in 2026. It answers from a fixed set of 11 documents: chokepoint traffic, war-risk insurance, JWC listed areas, canal fees, freight rates, fuel costs, supply chain pressure, country logistics scores and a risk playbook. Every answer cites the document and page it came from. When the documents don't cover a question, it says so instead of guessing.

## Purpose

Hormuz is shut for most commercial traffic. The Houthis have resumed attacks on ships in the Bab el-Mandeb. War-risk premiums moved from 0.25% of hull value to 7.5–10% in five months. The numbers behind those headlines sit in a dozen different reports. CLEARPATH puts them in one place, so someone can ask a plain question ("can cargo route through Suez right now, and what does cover cost?") and check the answer against the source.

## How I came up with it

My background is in political science. Conflicts like the Hormuz closure and the Red Sea attacks are political events, and they also show up in shipping data such as transit counts, insurance premiums, freight rates and fuel prices. I picked shipping because it connects the two. A RAG chatbot fit the project because the facts are in documents and each answer needs to point back to one.

Most of my design choices follow from that. The model gets the question together with numbered excerpts that passed a relevance gate and a system prompt that forbids outside knowledge. When no excerpt passes the gate, the app shows a fallback message and doesn't call the model.

---

## 1. Application identity

| | |
|---|---|
| **Name** | CLEARPATH · Supply Chain Intelligence |
| **Role** | Chatbot that answers supply chain risk and cost questions from a fixed document set |
| **Users** | Logistics, procurement, finance and risk staff |
| **Answers questions about** | Chokepoint traffic, war-risk insurance, JWC listed areas, Suez and Panama transit fees, container freight rates, bunker fuel, the NY Fed GSCPI, country logistics scores, and a supply chain risk playbook |
| **Knowledge base** | 11 documents: 9 PDF, 2 TXT. Market-data reports, crisis briefs, an insurance-market bulletin, and a policy playbook |
| **Data as of** | 22–26 November 2026 |

The app shows all of this in the header strip.

## 2. Knowledge base

| Code | Document | Format | Built from |
|---|---|---|---|
| SCI-01 | Global Chokepoint Traffic Monitor (week ending 22 Nov 2026) | PDF, 5 pp. | IMF PortWatch chokepoint database (ArcGIS API) and daily transit counts for 28 chokepoints |
| SCI-02 | Strait of Hormuz Crisis Brief 2026 | PDF | PortWatch, EIA, S&P Global Platts, Marsh, BRS, Insurance Journal, The National |
| SCI-03 | Red Sea, Bab el-Mandeb and Suez Canal Brief | PDF | Lloyd's List Intelligence, Drewry, Suez Canal Authority circulars, Africa Center, Xeneta |
| SCI-04 | Panama Canal Operations, Transit Slots and Fees 2026 | PDF | Panama Canal Authority advisories, gCaptain, Maritime Executive |
| SCI-05 | Marine War-Risk Insurance Pricing Bulletin | PDF | Marsh, BRS, WTW, Aon, Argus, S&P Global, Risk & Insurance |
| SCI-06 | JWC Listed Areas Register (JWLA-035) | PDF | Lloyd's Market Association, TT Club, HKSOA |
| SCI-07 | Container Freight Rate Report (Drewry WCI) | PDF | Drewry World Container Index, lane and composite history |
| SCI-08 | Bunker Fuel and Energy Cost Bulletin | TXT | ENGINE, Ship & Bunker, EIA World Oil Transit Chokepoints |
| SCI-09 | Global Supply Chain Pressure Index Brief | TXT | NY Fed GSCPI methodology and 2025–26 readings |
| SCI-10 | Country Logistics Performance Scorecard | PDF | World Bank LPI 2023 (API, 139 economies + aggregates) |
| SCI-11 | Supply Chain Risk Playbook | PDF | A policy document I wrote, with thresholds tied to the real data above |

The raw tables sit in `data/raw/` as ten CSVs, one per dataset, each with a source column. `scripts/build_knowledge_base.py` turns them into the documents. I kept that step in the repo so anyone can check where a number in a PDF came from.

There are two caveats about the data:

- My research tool read some pages through an extraction layer rather than downloading the raw file. To guard against transcription errors, `scripts/fetch_data.py` pulls the IMF PortWatch, World Bank LPI and NY Fed GSCPI data from the publishers' own endpoints. Run it and diff the output against `data/raw/`.
- Insurance premiums don't exist as an open dataset. Brokers quote them per voyage. The rate history in SCI-05 comes from broker statements reported in the trade press, with a citation on every row.

The playbook (SCI-11) gives the chatbot rules to apply. It sets risk tiers, routing rules (Suez versus the Cape), insurance approval limits and supplier rules, all keyed to indicators in the other ten documents. Questions that need two or three documents at once ("can cargo route through Suez right now, and what does cover cost?") depend on it.

## 3. Architecture

```mermaid
flowchart LR
  A[PDF / TXT documents] --> B[Load<br/>pypdf, per page]
  B --> C[Clean<br/>headers, footers,<br/>page numbers, wraps]
  C --> D[Chunk<br/>900 chars / 150 overlap<br/>page-bounded]
  D --> E[Embed<br/>text-embedding-3-small<br/>or nomic-embed-text]
  E --> F[(ChromaDB<br/>persistent, cosine)]
  Q[User question] --> QE[Embed query<br/>same model]
  QE --> R[Top-K search<br/>K = 5 OpenAI, 7 Ollama]
  F --> R
  R --> G{Relevance gate<br/>distance ≤ 0.62 OpenAI,<br/>≤ 0.40 Ollama}
  G -- no chunk passes --> FB[Fallback message]
  G -- pass --> P[Grounded prompt<br/>system rules + S1..Sn]
  P --> L[gpt-4o-mini<br/>or llama3.1:8b]
  L --> CI[Citations<br/>S# → doc, page, chunk]
  CI --> UI[Streamlit chat + source viewer]
```

What happens at each stage:

**Document.** Eleven files in `documents/`. The PDFs carry a running header, a footer and "Page X of Y" on every page, like real reports do.

**Load** (`rag/loader.py`). pypdf extracts text page by page, so every chunk keeps a true page number. TXT files load as one page. Encrypted files, image-only PDFs, empty files and corrupt files raise inside a per-file `try`; the loader records the error and moves to the next file. A bad document gets skipped instead of crashing the app, and the sidebar lists the skipped files.

**Clean** (`rag/cleaner.py`). Cleaning runs in four passes. Lines that repeat on 60% or more of a document's pages get treated as header or footer and dropped. Regex patterns remove page numbers and known boilerplate. Bullet glyphs that pypdf returns as control characters (`\x7f`) become `- `. Hard-wrapped lines rejoin into paragraphs, and words split by a hyphen at a line break rejoin into one word. Headings and bullets stay on their own lines because the chunker needs them.

**Chunk** (`rag/chunker.py`). See section 4.

**Embed** (`rag/embedder.py`). `text-embedding-3-small` (1,536 dimensions) on OpenAI, `nomic-embed-text` (768 dimensions) on Ollama, batches of 64. The same model embeds the questions. I set that in one place, `rag/config.py`, so the two can't drift apart.

**Store** (`rag/vectorstore.py`). A ChromaDB `PersistentClient` writing to `chroma_db/`, cosine distance. Each record holds the vector, the chunk text, a unique ID (`SCI-05_002_01` = document, page, chunk) and metadata: file name, document code, title, page, section, character count. Collection metadata holds a fingerprint: a SHA-256 over every document's bytes, plus the chunk settings and the embedding model name. On startup the app compares fingerprints. A match means the stored vectors get reused with zero embedding calls. A mismatch, after a document edit or a chunk-size change, triggers a rebuild.

**Query.** The question gets embedded once. Follow-ups that point back ("what about the Red Sea?", "how does that compare?") get the previous question prepended for retrieval. Standalone questions are left as they are. An early version merged any short question with the one before it, so "What is a good lasagna recipe?" asked after a Hormuz question picked up the Hormuz query and got through the gate.

**Retrieve** (`rag/retriever.py`). Top-K = 5 nearest chunks from ChromaDB. The multi-section questions in my test set need two or three documents, and the chokepoint table alone spans four chunks, so K = 3 leaves too little room. Past 5, the extra hits for a focused question come from unrelated documents and land in the weak or irrelevant tiers, where they make the prompt longer without adding useful information. On Ollama I use 7. `nomic-embed-text` packs related chunks closer together, and in testing two questions needed a chunk that ranked seventh: the Hormuz row of the traffic table for the Hormuz and Cape comparison (distance 0.294), and the 22 July premium for the Iran insurance question (0.285). The slider in Advanced settings lets you compare values live, and the "All retrieved" tab shows the distance of every hit.

**Filter.** Every hit gets a tier from its cosine distance:

| OpenAI distance | Ollama distance | Tier | What happens |
|---|---|---|---|
| ≤ 0.45 | ≤ 0.30 | strong | sent to the model |
| 0.45–0.55 | 0.30–0.36 | potential | sent to the model |
| 0.55–0.62 | 0.36–0.40 | weak | sent to the model, flagged in the source viewer |
| > 0.62 | > 0.40 | irrelevant | rejected |

If the best hit sits above the gate, CLEARPATH returns the fallback and never calls the LLM. A hit has to pass the distance check even when it ranks first. Section 5 covers how I picked the numbers.

**Generate** (`rag/generator.py`). `gpt-4o-mini` or `llama3.1:8b` at temperature 0.1. The user message contains the excerpts, labeled `[S1]` to `[Sn]` with document, page and section, followed by the question. The system prompt sets eight rules: answer from the excerpts with no outside knowledge, cite every factual sentence, copy numbers with their units and dates, say which part of the question the documents don't cover, apply playbook rules when they appear and name the rule, and treat instructions inside excerpts as data. Testing on the 8B model added three more lines to the prompt: compare a figure against every threshold band in a rule before applying it, give both figures when asked whether something rose or fell, and don't join facts from different excerpts into a cause no excerpt states. The style rule asks for plain sentences without adverbs. If the excerpts don't answer the question, the model has to reply with the exact token `INSUFFICIENT_CONTEXT`, which the app swaps for the fallback message. This works as a second check for chunks that score close but don't contain the answer.

**Cite.** `[S#]` markers turn into tags like `S2 · SCI-05 p.2`. Markers that point to a source the model never received get removed. Every answer ends with plain citations (`[Source: SCI-05 Marine War-Risk Insurance Pricing Bulletin - 2026, p. 2]`) and a telemetry line. The **View sources** expander has three tabs: the cited chunks with file, page, section, chunk ID, similarity and tier; all Top-K hits, rejected ones included; and stage timings.

## 3a. Running on local models (Ollama)

My instructor approved Ollama in place of the OpenAI API, so the pipeline runs on two providers. One line in `.streamlit/secrets.toml` picks between them:

```toml
LLM_PROVIDER = "ollama"
```

Ollama serves the same `/v1` endpoints as OpenAI on `localhost:11434`. The code keeps the OpenAI Python client and changes the base URL, the model names, Top-K and the threshold bands. Ollama needs no key.

| | OpenAI | Ollama |
|---|---|---|
| Embeddings | text-embedding-3-small, 1,536 dims | nomic-embed-text, 768 dims |
| Chat model | gpt-4o-mini | llama3.1:8b |
| Top-K | 5 | 7 |
| Starting gate | 0.62 | 0.40 |
| Bands (strong / potential / weak) | 0.45 / 0.55 / 0.62 | 0.30 / 0.36 / 0.40 |

The two embedding models put vectors in different spaces, and the index fingerprint includes the model name, so switching providers rebuilds `chroma_db/` on the next start. `RELEVANCE_THRESHOLD` and `OLLAMA_CHAT_MODEL` can be overridden in the same secrets file. I tested on an Apple M5 Pro with 48 GB of unified memory, where Ollama ran both models on the GPU through Metal.

## 4. Chunking strategy

Chunks are 900 characters with a 150-character overlap, and they never cross a page.

My documents mix two kinds of text. One is narrative ("the AWRP peaked near 2.5% in early March and eased to 1% by late March"). The other is data rows ("Suez Canal: 46 transits per day, +12% versus a year earlier…"). A data row runs 150–250 characters. A paragraph runs 400–900. At 900 characters a chunk holds one full paragraph or four to six rows, which comes to about 200 tokens and keeps each vector to one topic.

Smaller chunks (around 500) would cut paragraphs in half and separate numbers from the dates they refer to. Larger ones (around 1,500) would put Hormuz premiums and Red Sea premiums in one vector, which then sits halfway between two topics and matches neither question well.

The chunker packs whole blocks (headings, paragraphs, rows) and splits a block when that block runs past 900 characters on its own; then it splits at sentence boundaries. The overlap carries the last complete sentence or two into the next chunk, so a fact on a boundary stays retrievable. A heading never sits at the end of a chunk; it moves forward to open the next one. Chunks never cross a page break, which keeps page citations correct.

Each chunk gets a context header before embedding: `[SCI-05 | Marine War-Risk Insurance Pricing Bulletin - 2026 | 2. Rate history, 2025-2026]`. A row reading "2026-07-22 | Strait of Hormuz | hull war (AWRP): 7.5-10.0%" doesn't mention insurance on its own, so the header adds that context to the vector.

The knowledge base splits into 100 chunks of 217–939 characters, with a mean of 678.

## 5. Choosing the threshold

`scripts/calibrate_threshold.py` embeds 27 probe questions across five categories (direct, paraphrased, vague, misspelled, irrelevant) and records the best distance each one gets. The recommended gate is the midpoint between the worst answerable probe and the closest irrelevant one. The script writes everything to `tests/CALIBRATION.md`.

I used two rules to set it:

1. Misspelled and paraphrased questions have to pass. People misspell words, as in "wat hapend to the sues canal toll rebate", so the gate can't be too strict.
2. Irrelevant questions have to fail even when they sound business-like. "What will Bitcoin cost next year?" shares vocabulary with freight markets (price, next year) and is the hardest probe in the set.

Vague questions ("What's going on with shipping?") may land on either side. When one passes, the model writes a general briefing from what it retrieved, and the citations show which documents it drew on.

Measured on Ollama (`nomic-embed-text`, 100 chunks), from `tests/CALIBRATION.md`:

| Category | min | mean | max |
|---|---|---|---|
| direct | 0.146 | 0.194 | 0.231 |
| paraphrased | 0.265 | 0.317 | 0.355 |
| misspelled | 0.283 | 0.319 | 0.392 |
| vague | 0.303 | 0.380 | 0.436 |
| irrelevant | 0.404 | 0.511 | 0.564 |

The worst answerable probe is "hormuz insurence premuim july" at 0.392. The closest irrelevant probe is the Bitcoin question at 0.404, the hard case I expected; the World Cup question comes next at 0.459. The midpoint, 0.40, is my gate. That leaves 0.008 on each side. Because the margin is small, the second check matters. If a chunk passes the gate but doesn't contain the answer, the model returns `INSUFFICIENT_CONTEXT`.

I tried nomic's task prefixes (`search_document:` and `search_query:`) before settling on this. They made the separation worse. The worst answerable probe moved to 0.370 and Bitcoin to 0.356, so the two groups overlapped by 0.014. I dropped the prefixes.

The bands under the gate come from the same table. Every direct probe sits at or below 0.231, so strong ends at 0.30. Paraphrased probes reach 0.355, so potential ends at 0.36.

The OpenAI bands (0.45 / 0.55 / 0.62) are the values from before the switch. I have not re-run calibration on OpenAI embeddings. Distances depend on the embedding model and on this exact corpus, so a provider change means a new calibration run.

## 6. Performance

Documents get embedded once and stored. Each new question gets embedded and searched against what's stored.

Measured on Ollama (M5 Pro, `nomic-embed-text` and `llama3.1:8b`):

| Event | Embedding calls | Measured |
|---|---|---|
| First start, no `chroma_db/` | 100 chunks in 2 batches | 1.0 s (`status=built`) |
| Every later start | 0 | 0.0 s (`status=reused`) |
| Each question, median of 13 | 1 (the question) | embed 9 ms, search 1.3 ms, total 1,999 ms |
| Generation, median of the 9 answered questions | 0 | 2,703 ms |

The total median sits below the generation median because the four fallback questions skip generation. Most of the time goes to generation; embedding and search together take about 10 ms. The collection loads through `st.cache_resource`, so a Streamlit rerun doesn't reopen it. Every answer shows its total time, and the Telemetry tab in the source viewer breaks it into embedding, search and generation.

## 7. Error handling

| Failure | What the user sees |
|---|---|
| No API key (OpenAI provider) | A setup panel with the exact secrets line and where to put it; the app stops before any API call |
| Ollama not running (Ollama provider) | "Ollama not reachable" with the command to start it |
| Model not pulled (Ollama provider) | "Model not installed" naming the `ollama pull` it needs |
| Invalid key | "API key rejected" with a pointer to the secrets file |
| Rate limit or no credit | "Rate limit or quota reached" |
| Network down, timeout | "Network problem", conversation intact |
| Unreadable or empty document | Skipped; the warning names the file; the remaining documents still load |
| Empty knowledge base | "Knowledge base is empty"; chat disabled |
| ChromaDB error | Message suggesting deletion of `chroma_db/` to rebuild |
| Empty or whitespace input | Toast; nothing sent |
| Input over 1,000 characters | Blocked by the chat box |
| No relevant chunks | Fallback message plus a diagnostics table of the rejected hits |

`showErrorDetails = false` in `.streamlit/config.toml` keeps raw tracebacks out of the interface.

## 8. Interface

The visual direction mixes two references: the concept art for the first *Mirror's Edge* (white architecture, cool blue shadows, one red used for wayfinding) and the hazy, silvery album art of the ambient trio Purelink. I used them for mood and didn't copy either one.

- The base is off-white with blurred fog gradients and film grain, and the panels are frosted glass.
- Red is limited to citation tags, the route line in the header illustration and the hover state. *Mirror's Edge* uses red to mark the path through a level, and I used it to mark where a claim came from.
- Panels have chamfered corners instead of rounded ones, with 1-pixel borders.
- Fonts: Barlow Condensed for display, Barlow for text, Martian Mono for metadata.
- The header illustration is an SVG I drew in code: white rooftops shaped like container stacks, with a red route running over them past Hormuz, Bab el-Mandeb and the Cape.

The full header and the four-part summary strip show on the start screen. After the first question the header shrinks to a title bar, and the document list stays folded in the sidebar, so the conversation gets the space. Debug information lives inside the source viewer and the sidebar's "Advanced settings" expander, out of the main view. The Top-K and threshold sliders sit there for live testing.

## 9. Project layout

```
clearpath/
├── app.py                         Streamlit app
├── rag/
│   ├── config.py                  provider, models, chunk sizes, Top-K, threshold bands
│   ├── loader.py                  PDF/TXT extraction, per-file error capture
│   ├── cleaner.py                 header/footer/page-number removal, line repair
│   ├── chunker.py                 structure-aware, page-bounded chunking
│   ├── embedder.py                OpenAI or Ollama client, one model for docs and queries
│   ├── vectorstore.py             persistent ChromaDB + fingerprint rebuild logic
│   ├── retriever.py               Top-K search, tiers, threshold, follow-up handling
│   ├── generator.py               system prompt, grounded prompt, citation rendering
│   └── pipeline.py                one question, end to end, with timings
├── ui/  theme.py, components.py   design system and HTML components
├── documents/                     the 11 knowledge-base files
├── data/raw/                      10 source CSVs behind the documents
├── chroma_db/                     persistent vector store (commit it after ingest)
├── scripts/
│   ├── fetch_data.py              pull raw data from IMF / World Bank / NY Fed
│   ├── build_knowledge_base.py    CSVs → PDF/TXT documents
│   ├── ingest.py                  build or verify the vector store
│   ├── calibrate_threshold.py     probe distances → tests/CALIBRATION.md
│   └── run_tests.py               13-question evaluation → tests/TEST_REPORT.md
├── tests/
│   ├── test_questions.json        evaluation set
│   ├── test_pipeline_offline.py   11 pytest tests, no API key needed
│   └── fake_openai.py             offline stand-in client for tests
├── .streamlit/config.toml         theme, toolbar, error-detail settings
├── .streamlit/secrets.toml.example
├── requirements.txt
└── .gitignore                     excludes secrets.toml
```

## 10. Run it on your machine

With Ollama (install it from ollama.com/download first):

```bash
ollama pull nomic-embed-text && ollama pull llama3.1:8b
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
echo 'LLM_PROVIDER = "ollama"' > .streamlit/secrets.toml
pytest -q                                # 11 offline tests
python scripts/ingest.py                 # embeds the 100 chunks once, writes chroma_db/
python scripts/calibrate_threshold.py    # check the gate against your embeddings
python scripts/run_tests.py              # writes tests/TEST_REPORT.md
streamlit run app.py
```

With OpenAI, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste a key instead of the `LLM_PROVIDER` line. The key lives in `.streamlit/secrets.toml`. The code reads it through `st.secrets`, with `OPENAI_API_KEY` as an environment-variable fallback for the scripts. Nothing in the source contains a key, and `.gitignore` blocks the secrets file. Before the first push, run `git status` and make sure `secrets.toml` isn't listed.

## 11. Deploy to Streamlit Community Cloud

Streamlit Community Cloud can't reach an Ollama server on a laptop. A cloud deploy needs the OpenAI provider and a key, or an Ollama server the app can reach over the network. The `chroma_db/` folder must come from the same provider the deployed app uses.

1. Run `python scripts/ingest.py` on your machine and commit the `chroma_db/` folder along with the rest of the repo. The deployed app opens those vectors and makes zero embedding calls on boot. (Skip this step and the app builds the index on its first start instead, about 10 seconds, then reuses it until the container restarts.)
2. Push to a public GitHub repository.
3. At share.streamlit.io: **Create app** → pick the repo, branch `main`, file `app.py`.
4. **Advanced settings → Secrets**, paste `OPENAI_API_KEY = "sk-..."`, save.
5. Deploy. Check the five things the grader will check: the page loads, the status line reads "Knowledge base ready · 100 chunks", a direct question returns an answer with citations, an irrelevant question returns the fallback, and earlier messages stay on screen after a new one.

`requirements.txt` pins exact versions, so the ChromaDB that wrote `chroma_db/` on your machine is the same one that reads it in the cloud.

## 12. Testing

`tests/test_questions.json` holds 13 questions:

| Category | Count | Example |
|---|---|---|
| Direct | 4 | What was the Drewry WCI composite rate on 19 November 2026? |
| Paraphrased | 2 | How expensive has it become to insure a ship against war damage when sailing past Iran? |
| Misspelled | 1 | wat hapend to the sues canal toll rebate for big contaner ships |
| Multi-section | 2 | Compare current traffic through the Strait of Hormuz and the Cape of Good Hope, and explain how oil flows have shifted. |
| Irrelevant | 3 | Who won the 2022 FIFA World Cup? · What will the price of Bitcoin be next year? |
| Vague | 1 | What's going on with shipping? |

`scripts/run_tests.py` sends each one through the full pipeline and records five things per question: whether the expected document was retrieved, whether it was cited, whether the key facts appear in the answer, whether irrelevant questions got rejected, and the timings. Output goes to `tests/TEST_REPORT.md` and `tests/test_results.csv`. The report leaves an accuracy checkbox under each answer for a manual read against the cited page, because a substring match can't judge whether a sentence is right.

### Results (Ollama, llama3.1:8b, gate 0.40, Top-K 7)

**12/12 scored questions handled correctly.** All nine answerable questions got an answer that retrieved and cited the expected document. All three irrelevant questions got the fallback, the Bitcoin one at 0.404, four thousandths above the gate. The vague question fell back at 0.411 and stays out of the score.

Per-question record from the final run. "Accurate answer" comes from my manual read against the cited page.

| # | Category | Question | Best distance | Retrieved correct info | Accurate answer | Correct source cited | Correctly rejected |
|---|---|---|---|---|---|---|---|
| Q01 | Direct | What was the Drewry WCI composite rate on 19 November 2026? | 0.146 | Yes | Accurate | Yes (SCI-07) | n/a |
| Q02 | Direct | How many daily transits is the Panama Canal allowing after its 9 November 2026 advisory? | 0.195 | Yes | Partly | Yes (SCI-04) | n/a |
| Q03 | Direct | Which countries were added to the JWC listed areas in circular JWLA-033? | 0.177 | Yes | Accurate | Yes (SCI-06) | n/a |
| Q12 | Direct | Who has to approve a cargo war-risk premium of 1.2% of cargo value? | 0.244 | Yes | Wrong | Yes (SCI-11) | n/a |
| Q04 | Paraphrased | How expensive has it become to insure a ship against war damage when sailing past Iran? | 0.265 | Yes | Accurate | Yes (SCI-02) | n/a |
| Q05 | Paraphrased | Is there less strain on worldwide supply networks now than there was a month earlier? | 0.307 | Yes | Accurate | Yes (SCI-09) | n/a |
| Q06 | Misspelled | wat hapend to the sues canal toll rebate for big contaner ships | 0.289 | Yes | Accurate | Yes (SCI-03) | n/a |
| Q07 | Multi-section | Under the risk playbook, can we ship Asia-Europe cargo through Suez right now, and what is the latest Red Sea war-risk premium? | 0.173 | Yes | Accurate | Yes (SCI-11, SCI-03) | n/a |
| Q08 | Multi-section | Compare current traffic through the Strait of Hormuz and the Cape of Good Hope, and explain how oil flows have shifted. | 0.231 | Yes | Partly | Yes (SCI-01, SCI-02, SCI-03) | n/a |
| Q09 | Irrelevant | What is a good recipe for lasagna? | 0.564 | n/a | n/a | n/a | Yes |
| Q10 | Irrelevant | Who won the 2022 FIFA World Cup? | 0.459 | n/a | n/a | n/a | Yes |
| Q13 | Irrelevant (in-domain words) | What will the price of Bitcoin be next year? | 0.404 | n/a | n/a | n/a | Yes |
| Q11 | Vague (not scored) | What's going on with shipping? | 0.411 | n/a | n/a | n/a | Fell back, above the 0.40 gate |

The substring check found every key fact in 8 of the 9 answers. A manual read against the cited pages, recorded in `tests/TEST_REPORT.md`, gives 9 accurate, 2 partly, 1 wrong:

- Q02 (Panama) gives the right figure, 34 transits, then claims the advisory didn't state a transit number. The event log on SCI-04 page 2 does.
- Q08 (Hormuz and Cape) gets the traffic figures right, then claims oil moved from Hormuz to the Cape. The documents tie the 2023–24 rise at the Cape to the Red Sea crisis, two years before the Hormuz closure.
- Q12 (approval for a 1.2% cargo premium) names the CFO. The playbook puts anything above 0.5% with the VP Supply Chain and anything above 1.5% with the CFO, so the answer should be the VP Supply Chain. The chunk with the rule was the top hit.

Earlier runs had more problems, and each fix targeted one cause. Q08 and Q04 needed a chunk ranked seventh, a retrieval problem, so Top-K went from 5 to 7 on Ollama. Q12 named the CFO although the chunk holding the rule was retrieved, a prompt problem; a line telling the model to check every threshold band fixed it in most runs. Q05 never stated the September and October figures side by side, fixed with the rose-or-fell line.

I think the three remaining errors come from the limits of the 8B model. The right chunks reach the model in all three, and Q12 flips between the VP Supply Chain and the CFO from one run to the next with the same prompt. I tested further prompt wording three runs at a time, and every version that fixed one answer broke another. One made the model invent a playbook rule that doesn't exist. The table above shows the last run without changes.

`pytest -q` runs 11 offline tests that need no key. They check extraction and error capture on broken files, header and footer removal, line repair, chunk IDs and metadata, index persistence (the second start embeds nothing and a question embeds one string), the fallback on an irrelevant question, citation rendering (HTML escaped, invented source numbers dropped), and the follow-up rule that caused the lasagna bug.

## 13. Limits

- The data is a snapshot from late November 2026. War-risk rates move every 24–48 hours during a crisis.
- `llama3.1:8b` misreads some multi-part and rule-based questions (section 12). A larger local model is the next thing I'd test.
- The LPI scores come from the 2023 survey. The World Bank's newer LPI 2.0 uses shipment tracking data and isn't in this corpus.
- Retrieval matches meaning and can't do math. Ask "which chokepoint fell the most?" and the model reads the ranking out of one chunk; it doesn't compute it over all 28 rows. A tool call over the CSVs would fix that, and it's the next thing I'd build.

## 14. Reflection

**1. Which part of the assignment was the most challenging, and why?**

The front end. Getting Streamlit to look like a finished product took more attempts than any other part. The chat box covered the answers, the header filled the screen, and the sidebar listed every document at once. I used AI for part of this work. Organizing the data took the most time: ten CSVs from different publishers, each in its own format, turned into eleven documents with a source on every figure.

**2. Which Python concept do you feel most confident using?**

Working with data. Reading the CSVs into lists of dictionaries, cleaning them and writing them out as documents is the part I could explain without notes. The chunk metadata follows the same idea: a dictionary of document, page, section and chunk ID attached to every piece of text.

**3. How do you think companies like Netflix or Spotify use data structures and loops behind the scenes?**

I think they structure it much like this course teaches: lists of items, dictionaries of user data, and loops that score each item against what a user already likes. The main difference is scale. Their systems run across millions of users and fit each recommendation to one person's history in much more detail.

**4. What additional features would you add to improve this recommendation platform?**

For CLEARPATH I would add a tool that runs calculations over the CSVs, so a question like "which chokepoint fell the most?" gets calculated instead of read from one chunk. I would also try a larger local model, since `llama3.1:8b` misreads some rule-based questions, and add live data feeds in place of the November 2026 snapshot.

## 15. Why I think it's interesting

I think it's interesting because it's useful. A logistics or finance team could ask it a question and get an answer with the page it came from. The same setup would work in other fields where the information is in reports.
