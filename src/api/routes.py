import hmac
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Query, UploadFile

from src.ingestion.run import LOADERS

from . import config, service
from .state import rag
from .schemas import (AskRequest, AskResponse, DocumentList, Health, IngestJob,
                      SearchRequest, SearchResponse, build_ask_response, build_sources)


def require_key(x_api_key: str | None = Header(default=None)):
    if config.API_KEY and not hmac.compare_digest(x_api_key or "", config.API_KEY):
        raise HTTPException(401, "Missing or invalid X-API-Key header.")


public = APIRouter(prefix="/v1", tags=["system"])
secured = APIRouter(prefix="/v1", dependencies=[Depends(require_key)])




@public.get("/health", response_model=Health, summary="Liveness and chunks indexed per strategy")
def health():
    counts = service.index_stats()
    return Health(status="ok" if all(v is not None for v in counts.values()) else "degraded",
                  strategies=counts)

def _strategy(name: str | None) -> str:
    name = name or config.DEFAULT_STRATEGY
    if name not in config.STRATEGIES:
        raise HTTPException(422, f"strategy must be one of {config.STRATEGIES}")
    return name


@secured.post("/ask", response_model=AskResponse, tags=["query"],
              summary="Answer a question with verified citations and confidence scores")
def ask(req: AskRequest):
    strategy = _strategy(req.strategy)
    t0 = time.perf_counter()
    try:
        answer = rag.ask(req.question, strategy, req.mode)
    except FileNotFoundError:
        raise HTTPException(503, "Index not built yet. Run the seed or POST /v1/ingest.")
    except RuntimeError as e:                        # missing key, rate limit, provider error
        raise HTTPException(503, str(e)[:300])
    return build_ask_response(answer, strategy, req.mode,
                              int((time.perf_counter() - t0) * 1000))


@secured.post("/search", response_model=SearchResponse, tags=["query"],
              summary="Retrieval only (no LLM): ranked chunks with scores")
def search(req: SearchRequest):
    strategy = _strategy(req.strategy)
    t0 = time.perf_counter()
    try:
        rows = rag.search(req.question, strategy, req.mode, req.rerank)
    except FileNotFoundError:
        raise HTTPException(503, "Index not built yet. Run the seed or POST /v1/ingest.")
    return SearchResponse(strategy=strategy, mode=req.mode, rerank=req.rerank,
                          results=build_sources(rows),
                          latency_ms=int((time.perf_counter() - t0) * 1000))


@secured.get("/documents", response_model=DocumentList, tags=["documents"],
             summary="List ingested documents")
def documents(status: str | None = Query(None, pattern="^(ok|failed)$"),
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    total, items = service.list_documents(status, limit, offset)
    return DocumentList(total=total, items=items)


@secured.post("/ingest", response_model=IngestJob, status_code=202, tags=["documents"],
              summary="Upload documents (md, txt, html, pdf). Indexing runs in the background.")
async def ingest(background: BackgroundTasks, files: list[UploadFile] = File(...)):
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    supported = sorted(LOADERS)
    staged, names = [], []
    for f in files:
        name = Path(f.filename or "").name            # strips any path the client sent
        if Path(name).suffix.lower() not in LOADERS:
            raise HTTPException(415, f"Unsupported file {name!r}. Supported: {supported}")
        data = await f.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"{name!r} is larger than {config.MAX_UPLOAD_MB} MB")
        staged.append((name, data))
        names.append(name)

    job_id = service.new_job(names)
    folder = Path(config.INBOX) / job_id
    folder.mkdir(parents=True)
    for name, data in staged:
        (folder / name).write_bytes(data)
    background.add_task(service.run_job, job_id, str(folder))
    return IngestJob(**service.JOBS[job_id])


@secured.get("/ingest/{job_id}", response_model=IngestJob, tags=["documents"],
             summary="Status of an ingest job")
def ingest_status(job_id: str):
    if job_id not in service.JOBS:
        raise HTTPException(404, "Unknown job id.")
    return IngestJob(**service.JOBS[job_id])