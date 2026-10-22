import json
from src.chunking.chunker import fixed_split, recursive_split, chunk_document, CHUNK_SIZE
from src.chunking.chunker import merge_small_sections


def test_small_text_is_one_chunk():
    assert recursive_split("short text") == ["short text"]

def test_long_text_is_split():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 80 for i in range(20))
    for fn in (fixed_split, recursive_split):
        pieces = fn(text)
        assert len(pieces) > 1
        assert all(len(p) <= CHUNK_SIZE + 50 for p in pieces)

def test_chunks_record_their_strategy(tmp_path):
    section = {"text": "Hello world.", "source": "a.md", "doc_id": "abc",
               "heading_path": ["Setup"], "page": None, "format": "md"}
    (tmp_path / "v1.jsonl").write_text(json.dumps(section) + "\n")
    for strategy in ("fixed", "recursive"):
        chunks = chunk_document(tmp_path, strategy)
        assert chunks[0].strategy == strategy
        assert strategy in chunks[0].chunk_id
    assert chunk_document(tmp_path, "recursive")[0].text.startswith("Setup\n")
    assert chunk_document(tmp_path, "fixed")[0].text == "Hello world."


def _sec(path, text, page=7):
    return {"text": text, "heading_path": path, "page": page, "doc_id": "d",
            "source": "a.pdf", "format": "pdf"}

def test_small_siblings_merge_and_keep_leaf_heading():
    merged = merge_small_sections([
        _sec(["SIP", "Messages", "1. INVITE"], "Starts a call."),
        _sec(["SIP", "Messages", "2. ACK"], "Confirms it.")])
    assert len(merged) == 1
    assert merged[0]["heading_path"] == ["SIP", "Messages"]
    assert "1. INVITE" in merged[0]["text"] and "Confirms it." in merged[0]["text"]

def test_different_top_level_topics_do_not_merge():
    assert len(merge_small_sections([_sec(["JPEG"], "Short."),
                                     _sec(["MPEG"], "Short.")])) == 2