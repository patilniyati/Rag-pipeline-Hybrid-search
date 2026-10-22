from src.indexing import keyword


class SparseRetriever:
    def __init__(self, bm25_index: dict):
        self.index = bm25_index

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        """Returns (chunk_id, BM25 score), best first. Chunks with no keyword match are omitted."""
        return keyword.search_scored(self.index, query, k)