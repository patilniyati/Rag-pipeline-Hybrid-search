import argparse
import shutil
from pathlib import Path

from . import keyword
from .embedder import Embedder
from .pipeline import check_sync, index_chunks, load_chunks
from .settings import load_settings
from .store import open_store


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default="fixed", help="names the chunk set and the index")
    p.add_argument("--chunks-dir", help="default: data/chunks/<strategy>")
    p.add_argument("--rebuild", action="store_true", help="wipe this index first")
    p.add_argument("--check", action="store_true", help="verify Chroma and BM25 match")
    p.add_argument("--try", dest="query", help="test a query against both indexes")
    a = p.parse_args()

    s = load_settings()
    root = Path(s.index_root) / a.strategy

    if a.rebuild:
        shutil.rmtree(root, ignore_errors=True)
    if a.check:
        check_sync(s, a.strategy)
    elif a.query:
        store = open_store(a.strategy, s)
        print("\nBM25 (keywords):")
        for r in store.get(keyword.search(keyword.load(root / "bm25.pkl"), a.query, 3)):
            print(f"  {r['source']} p{r['page']} [{r['heading']}] {r['text'][:80]!r}")
        print("\nDense (meaning):")
        hits = store.col.query(query_embeddings=[Embedder(s).query(a.query).tolist()],
                               n_results=3)["ids"][0]
        for r in store.get(hits):
            print(f"  {r['source']} p{r['page']} [{r['heading']}] {r['text'][:80]!r}")
    else:
        folder = Path(a.chunks_dir) if a.chunks_dir else Path("data/chunks") / a.strategy
        print(index_chunks(load_chunks(folder), s, a.strategy))
        check_sync(s, a.strategy)


if __name__ == "__main__":
    main()