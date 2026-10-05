"""Core search contract, independently of model downloads and corpus quality."""
import pytest

from app.search import Searcher, SearchHit


def test_rrf_promotes_document_supported_by_both_retrievers(monkeypatch):
    searcher = Searcher()
    hit = lambda name: SearchHit(name, name, name, 999.0)
    monkeypatch.setattr(searcher, "_search_keyword", lambda q, k: [hit("kw"), hit("both")])
    monkeypatch.setattr(searcher, "_search_semantic", lambda q, k: [hit("sem"), hit("both")])
    results = searcher.search("query", mode="hybrid", top_k=3)
    assert results[0].doc_id == "both"
    assert results[0].score == pytest.approx(2 / 62)
    assert {h.doc_id for h in results} == {"kw", "sem", "both"}
    assert results[1].score == pytest.approx(1 / 61)


def test_search_rejects_unknown_mode():
    with pytest.raises(ValueError, match="unknown mode"):
        Searcher().search("query", mode="invalid")


def test_api_validates_input_and_returns_measured_response(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main

    class TinySearcher:
        size = 1

        def search(self, query, mode, top_k, rrf_k):
            return [SearchHit("cloud_001", "Cloud", "A document", 0.1)]

    monkeypatch.setattr(main.Searcher, "from_corpus", lambda path: TinySearcher())
    with TestClient(main.app) as client:
        assert client.get("/healthz").json() == {"ready": True, "n_docs": 1}
        result = client.get("/search", params={"q": "cloud", "mode": "hybrid"})
        assert result.status_code == 200
        body = result.json()
        assert body["latency_ms"] >= 0
        assert body["query"] == "cloud" and body["mode"] == "hybrid"
        assert body["hits"][0]["doc_id"] == "cloud_001"
        for params in ({"q": ""}, {"q": "x", "top_k": 0}, {"q": "x", "mode": "bad"}):
            assert client.get("/search", params=params).status_code == 422
