# Threshold calibration - 2026-11-26 21:27

Embedding model: `nomic-embed-text` · collection chunks: 100 · Top-K: 7

Best (top-1) cosine distance per probe. Lower = more similar.

| Category | Probe | Best distance | Top doc | Tier (current bands) |
|---|---|---|---|---|
| direct | What was the Drewry World Container Index composite rate on 19 November 2026? | 0.146 | SCI-07 | strong |
| direct | How many daily transits is the Panama Canal allowing after its 9 November 2026 advisory? | 0.195 | SCI-04 | strong |
| direct | Which countries were added to the JWC listed areas in circular JWLA-033? | 0.177 | SCI-06 | strong |
| direct | What was the war-risk premium for the Strait of Hormuz on 22 July 2026? | 0.186 | SCI-02 | strong |
| direct | What is Singapore's VLSFO average price in October 2026? | 0.227 | SCI-08 | strong |
| direct | What is Singapore's Logistics Performance Index score? | 0.231 | SCI-10 | strong |
| paraphrased | How expensive has it become to insure a ship against war damage when sailing past Iran? | 0.265 | SCI-05 | strong |
| paraphrased | Is there less strain on worldwide supply networks now than there was a month earlier? | 0.307 | SCI-09 | potential |
| paraphrased | How much does it cost to ship a box from China to the US East Coast these days? | 0.355 | SCI-07 | potential |
| paraphrased | Who signs off when insurance for a risky voyage gets very costly? | 0.355 | SCI-05 | potential |
| paraphrased | Which waterway has seen the biggest collapse in ship traffic? | 0.302 | SCI-01 | potential |
| vague | What's going on with shipping? | 0.411 | SCI-07 | irrelevant |
| vague | Is it risky right now? | 0.436 | SCI-11 | irrelevant |
| vague | Tell me about canals. | 0.368 | SCI-04 | weak |
| vague | fuel? | 0.303 | SCI-08 | potential |
| misspelled | wat hapend to the sues canal toll rebate for big contaner ships | 0.289 | SCI-03 | strong |
| misspelled | hormuz insurence premuim july | 0.392 | SCI-02 | weak |
| misspelled | panama canel auction recrod price | 0.312 | SCI-04 | potential |
| misspelled | drewery world contianer index latest | 0.283 | SCI-07 | strong |
| irrelevant | What is a good recipe for lasagna? | 0.564 | SCI-06 | irrelevant |
| irrelevant | Who won the 2022 FIFA World Cup? | 0.459 | SCI-10 | irrelevant |
| irrelevant | How do I fix a flat bicycle tire? | 0.552 | SCI-09 | irrelevant |
| irrelevant | Write me a poem about autumn. | 0.549 | SCI-07 | irrelevant |
| irrelevant | What is the capital of Australia? | 0.540 | SCI-01 | irrelevant |
| irrelevant | Explain how photosynthesis works. | 0.525 | SCI-09 | irrelevant |
| irrelevant | What will the price of Bitcoin be next year? | 0.404 | SCI-08 | irrelevant |
| irrelevant | Recommend a good laptop for gaming. | 0.495 | SCI-08 | irrelevant |

## Summary by category

| Category | min | mean | max |
|---|---|---|---|
| direct | 0.146 | 0.194 | 0.231 |
| paraphrased | 0.265 | 0.317 | 0.355 |
| vague | 0.303 | 0.380 | 0.436 |
| misspelled | 0.283 | 0.319 | 0.392 |
| irrelevant | 0.404 | 0.511 | 0.564 |

## Recommendation

- Worst answerable probe (direct/paraphrased/misspelled): **0.392**
- Closest irrelevant probe: **0.404**
- Separation gap: **0.013**
- Recommended `RELEVANCE_THRESHOLD`: **0.40** (currently 0.40)

Vague probes are reported but not used to set the gate: they may legitimately land on either side. When they pass the gate, the system prompt still forces the model to answer only from the retrieved chunks or return the fallback (second safety layer).

Update `rag/config.py` if the recommendation differs, then re-run `scripts/run_tests.py`.