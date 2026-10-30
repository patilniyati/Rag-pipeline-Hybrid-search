from pathlib import Path

from src.indexing import keyword
from src.indexing.embedder import Embedder
from src.indexing.settings import load_settings
from src.indexing.store import open_store
from .diversify import cap_per_source

from .dense import DenseRetriever
from .fusion import weighted_rrf
from .rerank import Reranker
from .settings import load_retrieval_settings
from .sparse import SparseRetriever


class Retriever:
    def __init__(self, strategy: str, index_settings=None, settings=None):
        idx = index_settings or load_settings()          # how the index was built
        self.s = settings or load_retrieval_settings()   # how we search it
        root = Path(idx.index_root) / strategy
        self.store = open_store(strategy, idx)
        self.dense = DenseRetriever(self.store, Embedder(idx))
        self.sparse = SparseRetriever(keyword.load(root / "bm25.pkl"))
        self._reranker = None                            # loaded only when first needed

    def search(self, query: str, mode: str = "hybrid", rerank: bool = True) -> list[dict]:
        """mode: "hybrid", "dense" or "sparse". rerank=False skips the second pass."""
        s = self.s
        hits = {}
        if mode in ("hybrid", "dense"):
            hits["dense"] = self.dense.search(query, s.dense_k)
        if mode in ("hybrid", "sparse"):
            hits["sparse"] = self.sparse.search(query, s.sparse_k)

        fused = weighted_rrf({name: [i for i, _ in h] for name, h in hits.items()},
                             {"dense": s.dense_weight, "sparse": s.sparse_weight},
                             s.rrf_k)[:s.rerank_candidates]
        rows = self._attach(fused, hits)

        if rerank and rows:
            if self._reranker is None:
                self._reranker = Reranker(s.reranker_model)
            ranked = self._reranker.rerank(query, rows, len(rows))     # keep all, ordered
            ranked = [r for r in ranked if r["rerank_score"] >= s.min_rerank_score]
            return cap_per_source(ranked, s.max_per_source, s.final_k)
        return cap_per_source(rows, s.max_per_source, s.final_k)

    def _attach(self, fused, hits):
        by_id = {r["id"]: r for r in self.store.get([cid for cid, _ in fused])}
        scores = {name: dict(h) for name, h in hits.items()}
        ranks = {name: {cid: n for n, (cid, _) in enumerate(h, 1)} for name, h in hits.items()}
        rows = []
        for cid, fused_score in fused:
            if cid not in by_id:
                continue
            row = by_id[cid]
            row["fused_score"] = round(fused_score, 5)
            for name in hits:
                row[f"{name}_rank"] = ranks[name].get(cid)
                row[f"{name}_score"] = scores[name].get(cid)
            rows.append(row)
        return rows