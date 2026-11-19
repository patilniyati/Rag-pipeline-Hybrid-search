

https://github.com/user-attachments/assets/0e69b208-8014-4cca-a168-b3babc7d8175



# Subtext: Hybrid-Search RAG over Internal Docs

A retrieval-augmented generation system for internal documentation. It combines dense and keyword search, reranks the results, answers only from retrieved context, and checks every citation with an LLM judge. It ships with an API, a dashboard, and an evaluation framework.

## Highlights

- **Hybrid retrieval:** dense (BGE embeddings in ChromaDB) plus BM25, merged with weighted Reciprocal Rank Fusion, then reranked by a cross-encoder.
- **Verified citations:** every claim in an answer is checked against the block it cites, and a composite confidence score is returned with the answer.
- **Honest refusals:** when the documents do not contain the answer, the system returns a structured "I don't know" with the closest documents to check manually.
- **Switchable chunking:** fixed, recursive, and semantic strategies, with the strategy recorded on every chunk. All three were compared on the same evaluation set.
- **Re-indexable:** raw files are stored by content hash, so loaders and chunkers can be improved without re-uploading anything.
- **Measured:** a 72-question golden set with a held-out test split that was run once.

## Architecture

```
Files (md, txt, html, pdf)
  -> Ingest   load, normalize, store raw by content hash, keep sections + metadata
  -> Chunk    fixed | recursive | semantic (strategy recorded per chunk)
  -> Index    ChromaDB (dense) + BM25 (sparse), dedup, kept in sync
  -> Retrieve dense + sparse -> weighted RRF -> cross-encoder rerank
  -> Generate answer only from numbered context blocks, cite [n]
  -> Verify   LLM judge checks each claim/citation, composite confidence
```

All of it is exposed through one entry point, `RagApp` (`src/app.py`), used by the API, the dashboard, and the command line.

## Quick start

### Docker

```bash
cp .env.example .env        # add GROQ_API_KEY
docker compose up --build
```

- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs

A one-shot `seed` service indexes `seed_corpus/` (a fictional 20-document engineering corpus) before the API starts. To serve more than one chunking strategy, set `STRATEGIES` in `docker-compose.yml` (for example `fixed,recursive,semantic`). Semantic chunking also needs `langchain-experimental` and `langchain-huggingface` in `requirements-api.txt`, and its embedding model baked into the image.

### Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-api.txt
cp .env.example .env        # add GROQ_API_KEY

python run.py --docs seed_corpus --strategies recursive      # build the indexes
python run.py --ask "What credentials are required to access the API?"

STRATEGIES=recursive uvicorn src.api.main:app                # terminal 1: API
streamlit run dashboard/app.py                               # terminal 2: dashboard
```

Run commands from the project root, so the theme in `.streamlit/` and the relative `data/` paths resolve. Do not use `--reload` for demos, since it drops the loaded models.

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/ask` | Answer with citations, confidence breakdown, and source chunks |
| `POST /v1/search` | Retrieval only (no LLM call): ranked chunks with scores |
| `GET /v1/documents` | List ingested documents |
| `POST /v1/ingest` | Upload documents; indexing runs as a background job (returns a job id) |
| `GET /v1/ingest/{job_id}` | Status of an ingest job |
| `GET /v1/health` | Chunks indexed per strategy |

Set `API_KEY` to require an `X-API-Key` header on everything except `/v1/health`.

```bash
curl -X POST localhost:8000/v1/ask -H "Content-Type: application/json" \
     -d '{"question": "What credentials are required to access the API?"}'
curl -F "files=@mydoc.pdf" localhost:8000/v1/ingest
```

## Dashboard

Ask a question and see the answer with clickable `[n]` citations, per-claim citation verdicts, a confidence breakdown (retrieval, citation coverage, completeness, composite), and the retrieved chunks ranked with their rerank, fused, dense, and sparse positions. A toggle compares hybrid and dense-only retrieval side by side. The comparison uses the search endpoint, so it makes no LLM calls.

## Configuration

| File | Controls |
|---|---|
| `index_config.json` | Embedding model, query/document prefixes, dedup threshold, index location |
| `retrieval_config.json` | `dense_k`, `sparse_k`, weights, `rerank_candidates`, `final_k`, reranker model |
| `generation_config.json` | LLM provider and model, context size, confidence threshold, reasoning effort |
| `eval_config.json` | Golden set path, judge model, delay between cases |
| `.env` | `GROQ_API_KEY` (never committed) |

Current retrieval settings: `dense_k` 20, `sparse_k` 20, `rerank_candidates` 30, `final_k` 8.

## Design decisions

- **Hybrid search.** BM25 matches exact identifiers (`DLQ-17`, `X-Northstar-Key`) that embeddings blur. Dense search handles paraphrases BM25 cannot. RRF merges by rank, so incompatible score scales (BM25 vs cosine) do not matter.
- **Reranking.** A cross-encoder reads the question and chunk together, which is more precise than comparing separate vectors but too slow for the whole corpus. Cheap searches pick 30 candidates and the reranker orders only those.
- **One source of truth.** BM25 is rebuilt from ChromaDB on every build, so the two indexes always hold the same chunks.
- **Dedup.** Cross-document only, cosine above 0.95, and chunks whose numbers differ are never merged ("15 days" is not a duplicate of "20 days").
- **Two refusal gates.** A low retrieval floor saves an LLM call on clearly unrelated questions. The model's own `INSUFFICIENT_CONTEXT` reply handles borderline cases, since it reads the actual text.
- **Single shared `RagApp`.** Models load once at startup instead of per request.
- **Background ingest.** Embedding takes longer than a request should, so `/v1/ingest` returns a job id.

## Evaluation

72 hand-written questions over the corpus: 30 lookup, 20 multi-hop, 12 unanswerable, 10 ambiguous. Split into 40 dev and 32 test. Settings were tuned on dev only, and the test split was run once with frozen settings. Each question moves a metric by about 2.5 points on dev and 3 points on test, so gaps of one or two questions are noise.

### Chunking strategy comparison

| Metric | fixed (dev / test) | recursive (dev / test) | semantic (dev / test) |
|---|---|---|---|
| Retrieval hit@8 | 0.97 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Retrieval MRR | 0.85 / 0.66 | 0.89 / 0.70 | 0.90 / 0.70 |
| Multi-hop: all evidence retrieved | 0.67 / 0.75 | 0.50 / 0.75 | 0.58 / 0.75 |
| Answer correctness | 0.93 / 0.89 | 0.91 / 0.89 | 0.89 / 0.88 |
| Citation accuracy | 0.94 / 0.94 | 0.92 / 0.94 | 0.92 / 0.96 |
| Citation coverage | 0.91 / 0.75 | 0.71 / 0.75 | 0.75 / 0.76 |
| Correct refusals (unanswerable) | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| False refusals (answerable) | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |

By question type, test correctness is 1.00 on lookup, 0.94 on multi-hop, and 1.00 on unanswerable for all three strategies. Ambiguous questions score 0.42 to 0.50 on test and 0.50 on dev for every strategy.

**Reading the comparison.** The strategies tie on answer quality within noise. Heading-prefixed chunks (recursive and semantic) rank the right chunk slightly higher than fixed-size chunks (MRR about +0.04 on both splits), which is the only consistent pattern. Recursive is the default because it matches semantic on quality without the build-time cost of embedding every sentence. No strategy is claimed to be best.

Citation coverage varied between dev runs (0.71 to 0.91) and converged on test (0.75 to 0.76), so treat it as a range rather than a strategy effect. Faithfulness is not used as a headline metric: it is scored 1.0 when every claim has a verified citation, so it largely mirrors citation coverage.

### Running the evaluation

```bash
python run_eval.py --validate                              # check the golden set against the corpus
python run_eval.py --retrieval-only                        # free: compares strategies on retrieval
python run_eval.py --sample 8 --strategies recursive       # small mixed smoke test
python run_eval.py --split dev --strategies recursive      # full dev run (uses LLM tokens)
python run_eval.py --split test --strategies recursive     # final run, once
```

Runs are saved under `eval/runs/<label>/`, resume with the same `--label`, stop cleanly when a provider's daily limit is hit, and record tokens per case. A full dev run costs roughly 140,000 tokens (about 3,500 per answered question).

### What tuning showed

- Raising `final_k` from 5 to 8 and the candidate pool from 20 to 30 raised full-evidence coverage on multi-hop questions from 4/12 to 8/12 (dev), with no regression on lookup hit rate or MRR. Failures were diagnosed by rank bucket (top-k, ranked 6 to 20, missing from the pool) before changing any setting.

### Tried and rejected

- **Per-source cap (2 or 3 chunks per document):** no net gain (one case up and one down at 2, no effect at 3). Implemented but disabled (`max_per_source: 0`).
- **Ambiguity rule in the prompt:** no change in the ambiguous-question score across two wordings.

## Known limitations

- **Ambiguous questions** score about 0.5. The system answers one reading, or blends them, instead of asking which is meant. Retrieval also misses about one expected source per ambiguous case.
- **Citation coverage is about 0.75.** Full-width citation brackets (`【n】`) are not parsed, so it may be understated.
- **Test MRR (0.66 to 0.70) is lower than dev (0.85 to 0.90).** The right chunk is always retrieved but ranks lower.
- **The answer model and the judge are the same model.** A hand check of 10 verdicts agreed 10 of 10, which is a small sample.
- **Hybrid vs dense-only is a design rationale, not a measured result.** That comparison has not been run.
- **Small, synthetic corpus** (20 documents, 91 chunks). Retrieval is easy at this size, and results do not generalize to other document sets.
- **No document replace or delete.** Re-uploading an edited file creates a new version and the old one stays indexed until removed manually.
- **Run-to-run variation.** A reasoning model can score the same question differently between runs, so single-case differences are not evidence.
- **Not production-ready:** one shared API key, no monitoring, and about 10 seconds per answered question because of the citation checks.

## Tests

```bash
python -m pytest -q
```

Covers loaders, chunker, dedup, fusion, per-source cap, citation parsing, evaluation matching and metrics, and the API (with the pipeline mocked, so no models or keys are needed).

## Project layout

```
src/
  ingestion/   loaders, normalization, raw store, manifest
  chunking/    fixed | recursive | semantic, small-section merging
  indexing/    embeddings, ChromaDB store, BM25, dedup, sync check
  retrieval/   dense, sparse, RRF, reranker, optional per-source cap
  generation/  prompt, LLM clients, citation verification, confidence
  evaluation/  golden set adapter, matching, judges, runner, report
  api/         FastAPI routes, schemas, ingest jobs
  app.py       RagApp: the single entry point
dashboard/     Streamlit UI (app.py, style.py)
eval/          golden set and run reports
seed_corpus/   sample documents for the Docker seed
run.py         one-command build / ask
run_eval.py    evaluation entry point
docker-compose.yml, Dockerfile.api, Dockerfile.dashboard
```

## Privacy note

With a hosted LLM provider, questions and retrieved document text are sent to that provider. The sample corpus is fictional and safe for this; use a local model (Ollama) for confidential documents.
