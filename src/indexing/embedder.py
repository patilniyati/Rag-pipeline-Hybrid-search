from .settings import Settings


class Embedder:
    def __init__(self, s: Settings):
        from sentence_transformers import SentenceTransformer
        self.s = s
        self.model = SentenceTransformer(s.model)

    def docs(self, texts: list[str]):
        return self.model.encode([self.s.doc_prefix + t for t in texts],
                                 batch_size=32, normalize_embeddings=True)

    def query(self, text: str):
        return self.model.encode([self.s.query_prefix + text],
                                 normalize_embeddings=True)[0]