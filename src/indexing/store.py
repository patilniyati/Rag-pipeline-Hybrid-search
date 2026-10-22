import chromadb
import numpy as np


class VectorStore:
    def __init__(self, path, model: str):
        client = chromadb.PersistentClient(path=str(path))
        self.col = client.get_or_create_collection(
            "chunks", metadata={"hnsw:space": "cosine", "model": model})
        if self.col.metadata.get("model") != model:
            raise RuntimeError("This index was built with a different model. "
                               "Run again with --rebuild.")

    def ids(self) -> set:
        return set(self.col.get(include=[])["ids"])

    def everything(self) -> list[dict]:
        g = self.col.get(include=["documents", "embeddings", "metadatas"])
        return [{"id": i, "text": t, "vec": np.asarray(v), "doc_id": m["doc_id"]}
                for i, t, v, m in zip(g["ids"], g["documents"],
                                      g["embeddings"], g["metadatas"])]

    def add(self, chunks: list[dict], vecs):
        for s in range(0, len(chunks), 500):               # Chroma limits batch size
            part = chunks[s:s + 500]
            self.col.upsert(ids=[c["chunk_id"] for c in part],
                            embeddings=[v.tolist() for v in vecs[s:s + 500]],
                            documents=[c["text"] for c in part],
                            metadatas=[_metadata(c) for c in part])

    def delete(self, ids: set):
        if ids:
            self.col.delete(ids=list(ids))

    def get(self, ids: list[str]) -> list[dict]:
        g = self.col.get(ids=ids, include=["documents", "metadatas"])
        by_id = dict(zip(g["ids"], zip(g["documents"], g["metadatas"])))
        return [{"id": i, "text": by_id[i][0], **by_id[i][1]} for i in ids if i in by_id]


def _metadata(c: dict) -> dict:
    # Chroma accepts only str/int/float/bool, so no lists and no None
    page = c.get("page")
    return {"doc_id": c["doc_id"], "source": c["source"],
            "chunk_index": int(c["chunk_id"].rsplit("-", 1)[1]),
            "heading": " > ".join(c.get("heading_path") or []),
            "strategy": c.get("strategy", ""), "char_count": len(c["text"]),
            "page": page if page is not None else -1, "format": c.get("format", "")}