from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000,
                          examples=["What credentials are required to access the API?"])
    strategy: str | None = Field(None, description="Which chunking-strategy index to search. "
                                                   "Defaults to the server default.")
    mode: Literal["hybrid", "dense", "sparse"] = "hybrid"


class SearchRequest(AskRequest):
    rerank: bool = Field(True, description="Apply the cross-encoder reranker.")


class Source(BaseModel):
    n: int = Field(..., description="Block number. Matches [n] in the answer text.")
    chunk_id: str
    source: str
    page: int | None = None
    heading: str = ""
    text: str
    rerank_score: float | None = None
    fused_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None


class Confidence(BaseModel):
    retrieval: float
    citation_coverage: float | None = None
    completeness: float | None = None
    missing_parts: list[str] = []
    composite: float


class Citation(BaseModel):
    claim: str
    cites: list[int]
    status: Literal["verified", "partial", "unsupported", "uncited"]
    checks: list[dict] = []


class AskResponse(BaseModel):
    status: Literal["answered", "insufficient"]
    answer: str
    confidence: Confidence
    citations: list[Citation] = []
    sources: list[Source] = []
    found: list[dict] = Field([], description="Only when insufficient: what retrieval did find.")
    not_found: str = ""
    suggested_documents: list[str] = []
    strategy: str
    mode: str
    latency_ms: int


class SearchResponse(BaseModel):
    strategy: str
    mode: str
    rerank: bool
    results: list[Source]
    latency_ms: int


class DocumentInfo(BaseModel):
    doc_id: str
    name: str
    format: str
    sections: int
    chars: int
    loader_version: str
    status: str
    error: str | None = None
    updated_at: str


class DocumentList(BaseModel):
    total: int
    items: list[DocumentInfo]


class IngestJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    files: list[str]
    error: str | None = None
    index: dict | None = None
    documents: list[DocumentInfo] = []


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    strategies: dict[str, int | None] = Field(..., description="Chunks indexed per strategy.")


def build_sources(chunks: list[dict]) -> list[Source]:
    out = []
    for n, c in enumerate(chunks, 1):
        page = c.get("page")
        out.append(Source(
            n=n, chunk_id=c["id"], source=c["source"],
            page=None if page in (None, -1) else page,
            heading=c.get("heading", ""), text=c["text"],
            rerank_score=c.get("rerank_score"), fused_score=c.get("fused_score"),
            dense_rank=c.get("dense_rank"), sparse_rank=c.get("sparse_rank")))
    return out


def build_ask_response(a, strategy: str, mode: str, ms: int) -> AskResponse:
    return AskResponse(
        status=a.status, answer=a.text,
        confidence=Confidence.model_validate(a.confidence),
        citations=[Citation.model_validate(c) for c in a.citations],
        sources=build_sources(a.contexts), found=a.found, not_found=a.not_found,
        suggested_documents=a.suggested_documents,
        strategy=strategy, mode=mode, latency_ms=ms)