# Chunking strategy comparison (20261022-0145-nogit-retrieval)

Bold = best in row. n/a = not measured in this run.

## Overall

| Metric | fixed | recursive | semantic |
|---|---|---|---|
| Cases scored | 40/40 | 40/40 | 40/40 |
| Retrieval hit@5 | **0.97** | **0.97** | 0.94 |
| Retrieval MRR | 0.85 | 0.89 | **0.90** |
| Multi-hop: all evidence retrieved | **0.33** | **0.33** | **0.33** |
| Answer correctness | n/a | n/a | n/a |
| Faithfulness | n/a | n/a | n/a |
| Citation accuracy | n/a | n/a | n/a |
| Citation coverage | n/a | n/a | n/a |
| Correct refusals (unanswerable) | n/a | n/a | n/a |
| False refusals (answerable questions) | n/a | n/a | n/a |

## By question type (correctness, or retrieval hit@5 in a retrieval-only run)

| Type | fixed | recursive | semantic |
|---|---|---|---|
| ambiguous | n/a | n/a | n/a |
| lookup | **1.00** | **1.00** | **1.00** |
| multi_hop | **0.92** | **0.92** | 0.83 |
| unanswerable | n/a | n/a | n/a |

## Cases where strategies disagree (read these first)

- G031: fixed 1.0, recursive 1.0, semantic 0.0

Each case moves a metric by about 1/n, so gaps of one or two cases are noise.