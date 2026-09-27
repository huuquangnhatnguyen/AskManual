"""AS2.1: the harness itself, run against the keyword stand-in over fixture chunks."""
from eval.metrics import citation_correct, first_rank, gold_pages, hit_at_k
from eval.run import evaluate, groups, load_gold, render
from retrieval.base import Hit
from retrieval.keyword import KeywordRetriever

G = {"id": "T1", "query_type": "fault_code", "cross_manual": False, "scan_target": False,
     "question": "ACS580 fault 2330 earth leakage", "doc_id": "acs580_firmware_manual", "page": 553}


def test_gold_set_is_well_formed():
    gold = load_gold()
    assert len(gold) == 25
    assert all({"id", "question", "query_type", "doc_id", "page"} <= set(g) for g in gold)


def test_also_supported_by_counts_as_gold():
    g = {**G, "also_supported_by": [{"doc_id": "other", "page": 9}]}
    assert gold_pages(g) == {("acs580_firmware_manual", 553), ("other", 9)}
    assert hit_at_k([Hit("x", "other", 9, 1.0)], g)


def test_recall_respects_k():
    hits = [Hit(str(i), "d", i, 1.0) for i in range(1, 6)] + [Hit("g", "acs580_firmware_manual", 553, 0.1)]
    assert not hit_at_k(hits, G, k=5)
    assert hit_at_k(hits, G, k=6)
    assert first_rank(hits, G) == 6


def test_groups_overlap_but_overall_counts_once():
    assert groups({**G, "cross_manual": True, "scan_target": True}) == ["fault_code", "cross_manual", "scanned", "OVERALL"]


def test_evaluate_swaps_retrievers_without_code_changes(fixture_chunks):
    result = evaluate(KeywordRetriever(fixture_chunks), [G], k=5)
    assert result["retriever"] == "keyword"
    assert result["table"]["OVERALL"] == {"n": 1, "hits": 1, "cite_ok": 0}
    assert "fault_code" in render(result)


def test_citation_correct():
    assert citation_correct({("acs580_firmware_manual", 553)}, G)
    assert not citation_correct({("acs580_firmware_manual", 535)}, G)
