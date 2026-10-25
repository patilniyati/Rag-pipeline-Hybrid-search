from fastapi.testclient import TestClient

from src.api import config
from src.api.main import app
from src.api.state import rag
from src.generation.answer import Answer

ROW = {"id": "c1", "source": "a.md", "page": -1, "heading": "H", "text": "Keys go in a header.",
       "rerank_score": 2.0, "fused_score": 0.03, "dense_rank": 1, "sparse_rank": None}


def _fake_ask(q, strategy=None, mode="hybrid"):
    return Answer(
        status="answered", text="Keys go in a header [1].",
        confidence={"retrieval": 0.9, "citation_coverage": 1.0, "completeness": 1.0,
                    "missing_parts": [], "composite": 0.95},
        citations=[{"claim": "Keys go in a header.", "cites": [1], "checks": [],
                    "status": "verified"}],
        contexts=[ROW])


def _client(monkeypatch):
    monkeypatch.setattr(rag, "ask", _fake_ask)
    monkeypatch.setattr(rag, "search", lambda q, s=None, m="hybrid", r=True: [ROW])
    return TestClient(app)          # no `with`, so the warm-up is skipped


def test_ask_returns_answer_sources_and_confidence(monkeypatch):
    r = _client(monkeypatch).post("/v1/ask", json={"question": "how do keys work"})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "answered"
    assert body["sources"][0]["n"] == 1 and body["sources"][0]["page"] is None
    assert body["confidence"]["composite"] == 0.95


def test_search_returns_ranked_chunks(monkeypatch):
    r = _client(monkeypatch).post("/v1/search", json={"question": "keys", "mode": "dense"})
    assert r.status_code == 200 and r.json()["results"][0]["chunk_id"] == "c1"


def test_unknown_strategy_is_rejected(monkeypatch):
    r = _client(monkeypatch).post("/v1/ask", json={"question": "hello there", "strategy": "nope"})
    assert r.status_code == 422


def test_api_key_is_enforced_when_configured(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(config, "API_KEY", "secret")
    body = {"question": "how do keys work"}
    assert client.post("/v1/ask", json=body).status_code == 401
    assert client.post("/v1/ask", json=body, headers={"X-API-Key": "secret"}).status_code == 200


def test_ingest_rejects_unsupported_files(monkeypatch):
    r = _client(monkeypatch).post("/v1/ingest", files=[("files", ("x.exe", b"abc"))])
    assert r.status_code == 415