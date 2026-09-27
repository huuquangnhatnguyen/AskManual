"""Retriever contract and registry. Run: pytest tests/"""
import pytest

from retrieval import registry
from retrieval.base import Hit, Retriever
from retrieval.confidence import should_refuse, top_score
from retrieval.keyword import KeywordRetriever


def test_registry_names_every_planned_retriever():
    assert {"keyword", "baseline", "dense", "bm25", "fused"} <= set(registry.names())


def test_unknown_retriever_names_the_options():
    with pytest.raises(KeyError, match="registered"):
        registry.get("nope")


def check_contract(r: Retriever, query: str, k: int = 3) -> list[Hit]:
    """What every retriever owes its callers. Reuse this when adding one."""
    assert isinstance(r, Retriever)
    hits = r.search(query, k=k)
    assert len(hits) <= k
    assert all(isinstance(h, Hit) and h.page >= 1 for h in hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)
    return hits


def test_keyword_retriever_meets_contract(fixture_chunks):
    hits = check_contract(KeywordRetriever(fixture_chunks), "earth leakage fault 2330")
    assert hits and hits[0].page == 553


def test_keyword_retriever_filters_by_family(fixture_chunks):
    r = KeywordRetriever(fixture_chunks)
    assert r.search("earth leakage", product_family="ACS880") == []
    assert r.search("earth leakage", product_family="ACS580")


def test_baseline_meets_contract(pending):
    from retrieval.baseline import CACHE
    if not CACHE.exists():
        pytest.skip("index/baseline.npz not built: python -m retrieval.baseline")
    with pending():
        hits = check_contract(registry.get("baseline"), "ACS580 fault 2330 earth leakage", k=5)
        assert hits


def test_confidence_gate():
    hits = [Hit("a", "d", 1, 0.03), Hit("b", "d", 2, 0.01)]
    assert top_score(hits) == 0.03
    assert should_refuse(hits, threshold=0.05)
    assert not should_refuse(hits, threshold=0.02)
    assert should_refuse([], threshold=0.001)
