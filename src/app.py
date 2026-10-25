import threading
from pathlib import Path

from src.chunking.chunker import chunk_all
from src.generation.answer import Answer, Answerer
from src.indexing.pipeline import check_sync, index_chunks, load_chunks
from src.indexing.settings import load_settings
from src.ingestion.run import add


class RagApp:
    def __init__(self, strategies=("recursive",), default="recursive"):
        self.strategies = list(strategies)
        self.default = default
        self._answerers: dict[str, Answerer] = {}
        self._lock = threading.Lock()          # guards the cache
        self._build_lock = threading.Lock()    # one build at a time

    # ---- query side
    def _answerer(self, strategy: str | None) -> Answerer:
        strategy = strategy or self.default
        if strategy not in self.strategies:
            raise ValueError(f"strategy must be one of {self.strategies}")
        with self._lock:
            if strategy not in self._answerers:
                self._answerers[strategy] = Answerer(strategy)
            return self._answerers[strategy]

    def ask(self, question: str, strategy=None, mode="hybrid") -> Answer:
        return self._answerer(strategy).ask(question, mode=mode)

    def search(self, question: str, strategy=None, mode="hybrid", rerank=True) -> list[dict]:
        return self._answerer(strategy).retriever.search(question, mode=mode, rerank=rerank)

    # ---- build side
    def ingest(self, folder: str) -> dict:
        """Raw store -> sections -> chunks -> both indexes, for every served strategy."""
        with self._build_lock:
            add(folder)
            s, stats = load_settings(), {}
            for name in self.strategies:
                chunk_all(name)
                stats[name] = index_chunks(load_chunks(Path("data/chunks") / name), s, name)
            with self._lock:
                self._answerers.clear()        # reload BM25 files on next query
            return stats

    def status(self) -> dict:
        s = load_settings()
        return {name: check_sync(s, name) for name in self.strategies}