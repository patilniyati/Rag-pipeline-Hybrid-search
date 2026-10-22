class DenseRetriever:
    def __init__(self, store, embedder):
        self.store, self.embedder = store, embedder

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        """Returns (chunk_id, cosine similarity), best first."""
        n = min(k, self.store.col.count())
        if n == 0:
            return []
        res = self.store.col.query(
            query_embeddings=[self.embedder.query(query).tolist()],
            n_results=n, include=["distances"])
        # the collection uses cosine distance, so similarity = 1 - distance
        return [(i, 1.0 - d) for i, d in zip(res["ids"][0], res["distances"][0])]