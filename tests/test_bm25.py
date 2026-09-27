"""AS2.3 / AS3.1: build_bm25 round-trips through the pickle BM25Retriever loads."""
from retrieval.bm25 import BM25Retriever
from retrieval.index import build_bm25


def test_bm25_round_trip_finds_fault_code(fixture_chunks, tmp_path):
    path = tmp_path / "bm25.pkl"
    assert build_bm25(list(fixture_chunks.values()), path) == len(fixture_chunks)
    hits = BM25Retriever(path).search("fault 2330 earth leakage", k=3)
    assert hits and hits[0].page == 553
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_bm25_filters_by_product_family(fixture_chunks, tmp_path):
    path = tmp_path / "bm25.pkl"
    build_bm25(list(fixture_chunks.values()), path)
    r = BM25Retriever(path)
    assert r.search("earth leakage 2330", k=5, product_family="NO_SUCH_FAMILY") == []
    fams = {f for c in fixture_chunks.values() for f in c.product_family}
    for fam in fams:
        for h in r.search("fault", k=10, product_family=fam):
            assert fam in fixture_chunks[h.chunk_id].product_family


def test_bm25_no_match_returns_nothing(fixture_chunks, tmp_path):
    path = tmp_path / "bm25.pkl"
    build_bm25(list(fixture_chunks.values()), path)
    assert BM25Retriever(path).search("zzqx", k=5) == []
