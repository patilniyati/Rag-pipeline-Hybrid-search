class Reranker:
    """Cross-encoder: reads the question and one chunk together and scores their relevance."""

    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)         # first run downloads ~90 MB

    def rerank(self, query: str, rows: list[dict], top_n: int) -> list[dict]:
        scores = self.model.predict([(query, r["text"]) for r in rows])
        for row, score in zip(rows, scores):
            row["rerank_score"] = float(score)        # raw logit: only the order matters
        return sorted(rows, key=lambda r: r["rerank_score"], reverse=True)[:top_n]