from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import config
from .routes import public, secured
from .state import rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        rag.search("warm up", rerank=False)          # loads models; makes no LLM call
    except Exception as e:
        print(f"warm-up skipped: {e}")
    yield


app = FastAPI(
    title="Internal Docs RAG API", version="1.0.0", lifespan=lifespan,
    description="Hybrid-search RAG over internal documentation. Answers carry bracketed "
                "citations, each verified by an LLM judge, plus a confidence breakdown.")
app.include_router(public)
app.include_router(secured)