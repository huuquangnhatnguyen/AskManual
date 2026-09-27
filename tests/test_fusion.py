"""AS3.1: reciprocal rank fusion, k=60. These pin rrf() before it exists."""
import pytest

from retrieval.base import Hit
from retrieval.fusion import RRF_K, FusedRetriever, rrf


def h(cid: str, score: float = 1.0) -> Hit:
    return Hit(cid, "doc", 1, score)


def test_rrf_scores_are_reciprocal_ranks(pending):
    with pending():
        fused = rrf([[h("a"), h("b")], [h("b"), h("c")]])
    scores = {x.chunk_id: x.score for x in fused}
    assert scores["b"] == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert scores["a"] == pytest.approx(1 / (RRF_K + 1))
    assert scores["c"] == pytest.approx(1 / (RRF_K + 2))
    assert [x.chunk_id for x in fused] == ["b", "a", "c"]


def test_rrf_ignores_input_scores(pending):
    # BM25 scores in the hundreds must not swamp cosines under 1 — only ranks count.
    with pending():
        fused = rrf([[h("a", 900.0)], [h("b", 0.2)]])
    assert fused[0].score == pytest.approx(fused[1].score)


def test_rrf_ties_break_deterministically(pending):
    with pending():
        once = rrf([[h("z")], [h("m")]])
        again = rrf([[h("m")], [h("z")]])
    assert [x.chunk_id for x in once] == [x.chunk_id for x in again] == ["m", "z"]


def test_rrf_keeps_hit_metadata(pending):
    with pending():
        fused = rrf([[Hit("a", "acs580_firmware_manual", 553, 0.9)]])
    assert (fused[0].doc_id, fused[0].page) == ("acs580_firmware_manual", 553)


def test_fused_retriever_fuses_its_inputs(pending, fixture_chunks):
    from retrieval.keyword import KeywordRetriever
    kw = KeywordRetriever(fixture_chunks)
    with pending():
        hits = FusedRetriever([kw, kw]).search("earth leakage 2330", k=2)
    assert hits and hits[0].page == 553
